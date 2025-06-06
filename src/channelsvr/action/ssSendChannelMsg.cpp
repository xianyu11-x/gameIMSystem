#include "channelsvr/channelServer.h"
#include "common/BaseMsg.pb.h"
#include "coroio/corochain.hpp"
#include "util/uuid.hpp"
#include <unordered_set>

TFuture<void> channelServer::ssSendChannelMsg(const int socketFd,
                                              const std::string &message,
                                              std::string &response) {
  protocol::sschannelmsg::SSChannelMsgReq req;
  req.ParseFromString(message);
  protocol::sschannelmsg::SSChannelMsgRsp rsp;
  rsp.set_msgtype(req.msgtype());

  // 合法性校验
  auto sendPlayer = req.sendplayer();
  auto sendPlayerName = sendPlayer.playername();
  auto sendPlayerId = redis_ptr->get("username:" + sendPlayerName);
  if (!sendPlayerId) {
    logger->error("Send player not found, player name: {}", sendPlayerName);
    rsp.set_issuccess(false);
    rsp.set_errmsg("Send player not found");
    response = rsp.SerializeAsString();
    co_return;
  }
  sendPlayer.set_playerid(stoll(sendPlayerId.value()));

  auto channelInfo = req.channelinfo();
  auto channelName = req.channelinfo().channelname();
  auto channelId = redis_ptr->get("channelName:" + channelName);
  if (!channelId) {
    logger->error("Channel not found, channel name: {}", channelName);
    rsp.set_issuccess(false);
    rsp.set_errmsg("Channel not found");
    response = rsp.SerializeAsString();
    co_return;
  }

  // 检查发送者是否是频道的成员
  if (!redis_ptr->sismember("channel:member:" + channelId.value(),
                            sendPlayerId.value())) {
    logger->error(
        "Player {} is not a member of channel {}, cannot send message",
        sendPlayerName, channelName);
    rsp.set_issuccess(false);
    rsp.set_errmsg("Player is not a member of the channel");
    response = rsp.SerializeAsString();
    co_return;
  }

  int msgSize = req.chatmessage_size();
  int64_t msgSeq = 0;
  std::vector<protocol::common::chatMessage> chatMessageList;
  for (int i = 0; i < msgSize; i++) {
    auto chatMessage = req.chatmessage(i);
    chatMessage.set_id(generateUUID());
    msgSeq = redis_ptr->incr("channel:seq:" + channelId.value());
    chatMessage.set_seq(msgSeq);
    chatMessage.set_allocated_sendplayer(
        new protocol::common::PlayerInfo(sendPlayer));
    redis_ptr->zadd("channel:message:" + channelId.value(),
                    chatMessage.SerializeAsString(),
                    static_cast<double>(msgSeq));
    chatMessageList.push_back(chatMessage);
  }

  // 获取广播消息
  std::unordered_set<std::string> members;
  std::string onlineSetKey = "onlineSet";
  std::string channelMemberKey = "channel:member:" + channelId.value();
  redis_ptr->sinter({onlineSetKey, channelMemberKey}, members.begin());
  members.erase(sendPlayerId.value());
  ssPushChannelMsg(members, channelInfo, sendPlayer, chatMessageList,
                   protocol::common::MsgSender::EN_MSG_SENDER_CHANNELSVR);

  // 返回响应
  rsp.set_issuccess(true);
  rsp.set_allocated_sendplayer(new protocol::common::PlayerInfo(sendPlayer));
  response = rsp.SerializeAsString();
  logger->info(
      "Send channel message success, channel name: {}, send player: {}",
      channelName, sendPlayerName);
  co_return;
}