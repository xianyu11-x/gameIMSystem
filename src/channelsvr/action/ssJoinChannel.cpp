#include "channelsvr/channelServer.h"
#include "common/channel.pb.h"
#include "coroio/corochain.hpp"
#include <vector>

TFuture<void> channelServer::ssJoinChannel(const int socketFd,
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

  auto channelName = req.channelinfo().channelname();
  auto channelId = redis_ptr->get("channelName:" + channelName);
  if (!channelId) {
    logger->error("Channel not found, channel name: {}", channelName);
    rsp.set_issuccess(false);
    rsp.set_errmsg("Channel not found");
    response = rsp.SerializeAsString();
    co_return;
  }

  // 加入频道
  redis_ptr->sadd("channel:member:" + channelId.value(), sendPlayerId.value());

  logger->info("Player {} joined channel {}", sendPlayerName, channelName);

  // 获取频道信息和成员列表
  auto channelInfoStr = redis_ptr->get("channel:" + channelId.value());
  if (!channelInfoStr) {
    logger->error("Channel info not found, channel id: {}", channelId.value());
    rsp.set_issuccess(false);
    rsp.set_errmsg("Channel info not found");
    response = rsp.SerializeAsString();
    co_return;
  }
  protocol::common::channelInfo channelInfo;
  channelInfo.ParseFromString(channelInfoStr.value());

  std::vector<std::string> members;
  redis_ptr->smembers("channel:member:" + channelId.value(),
                      std::back_inserter(members));
  for (const auto &memberId : members) {
    auto memberInfo = redis_ptr->get("user:" + memberId);
    if (memberInfo) {
        protocol::common::PlayerInfo playerInfo;
        playerInfo.ParseFromString(memberInfo.value());
        channelInfo.add_members()->CopyFrom(playerInfo);
    }
  }

  // 返回响应
  rsp.set_issuccess(true);
  rsp.set_allocated_sendplayer(new protocol::common::PlayerInfo(sendPlayer));
  rsp.add_channelinfo()->CopyFrom(channelInfo);
  response = rsp.SerializeAsString();
  co_return;
}