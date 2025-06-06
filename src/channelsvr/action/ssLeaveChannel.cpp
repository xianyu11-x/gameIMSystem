#include "channelsvr/channelServer.h"
#include "common/channel.pb.h"
#include "coroio/corochain.hpp"

TFuture<void> channelServer::ssLeaveChannel(const int socketFd,
                                            const std::string &message,
                                            std::string &response) {
  protocol::ssmsg::SSMsgReq ssMsgReq;
  ssMsgReq.ParseFromString(message);
  auto req = ssMsgReq.channelreq();
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

  // 离开频道
  redis_ptr->srem("channel:member:" + channelId.value(), sendPlayerId.value());

  logger->info("Player {} left channel {}", sendPlayerName, channelName);

  // 返回响应
  rsp.set_issuccess(true);
  rsp.set_allocated_sendplayer(new protocol::common::PlayerInfo(sendPlayer));
  protocol::ssmsg::SSMsgRsp ssMsgRsp;
  ssMsgRsp.set_msgtype(ssMsgReq.msgtype());
  ssMsgRsp.set_allocated_channelrsp(
      new protocol::sschannelmsg::SSChannelMsgRsp(rsp));
  response = ssMsgRsp.SerializeAsString();
  co_return;
}