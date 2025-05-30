#include "chatsvr/chatServer.h"
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "coroio/corochain.hpp"
#include "util/uuid.hpp"
#include <utility>

TFuture<void> chatServer::ssSendChatMsg(const int socketFd,
                                        const std::string &message,
                                        std::string &response) {
  protocol::ssmsg::SSMsgReq req;
  req.ParseFromString(message);
  auto ssChatMsg = req.chatreq();

  protocol::ssmsg::SSMsgRsp rsp;
  rsp.set_msgtype(req.msgtype());
  auto chatRsp = rsp.mutable_chatrsp();
  chatRsp->set_msgtype(ssChatMsg.msgtype());

  auto sendPlayerName = ssChatMsg.sendplayer().playername();
  auto receivePlayerName = ssChatMsg.receiveplayer().playername();
  // 检查玩家是否存在
  auto sendPlayerId = redis_ptr->get("username:" + sendPlayerName);
  auto receivePlayerId = redis_ptr->get("username:" + receivePlayerName);
  if (!sendPlayerId) {
    std::cerr << "Send player not found" << std::endl;
    logger->error("Send player not found, player name: {}", sendPlayerName);
    chatRsp->set_issuccess(false);
    chatRsp->set_errmsg("Send player not found");
    response = rsp.SerializeAsString();
    co_return;
  }
  if (!receivePlayerId) {
    std::cerr << "Receive player not found" << std::endl;
    logger->error("Receive player not found, player name: {}",
                  receivePlayerName);
    chatRsp->set_issuccess(false);
    chatRsp->set_errmsg("Receive player not found");
    response = rsp.SerializeAsString();
    co_return;
  }
  // 消息保存
  int64_t msgSeq = 0;
  for (int i = 0; i < ssChatMsg.chatmessage_size(); i++) {
    auto chatMessage = ssChatMsg.chatmessage(i);
    chatMessage.set_id(generateUUID());
    msgSeq =
        redis_ptr->incr("chat:seq:" + *sendPlayerId + ":" + *receivePlayerId);
    chatMessage.set_seq(msgSeq);
    redis_ptr->zadd("chat:message:" + *sendPlayerId + ":" + *receivePlayerId,
                    chatMessage.SerializeAsString(),
                    static_cast<double>(msgSeq));
  }
  // 检查玩家是否在线
  if (redis_ptr->sismember("onlineSet", *receivePlayerId)) {
    ssPushMsg(ssChatMsg, protocol::common::MsgSender::EN_MSG_SENDER_CHATSVR,
              msgSeq);
  }else{
    redis_ptr->hmset("chat:unread:" + *receivePlayerId,
                     {std::make_pair(*sendPlayerId, msgSeq)});
  }
  chatRsp->set_allocated_sendplayer(
      new protocol::common::PlayerInfo(ssChatMsg.sendplayer()));
  chatRsp->set_issuccess(true);
  response = rsp.SerializeAsString();
  logger->info("Send message success, send player: {}, receive player: {}",
               sendPlayerName, receivePlayerName);
  co_return;
}