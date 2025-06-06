#include "channelsvr/channelServer.h"
#include "common/SSMsg.pb.h"
#include "common/channel.pb.h"
#include "coroio/corochain.hpp"

TFuture<void> channelServer::ssCreateChannel(const int socketFd,
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
  auto checkedChannelId = redis_ptr->get("channelName:" + channelName);
  if (checkedChannelId) {
    logger->error("Channel already exists, channel name: {}", channelName);
    rsp.set_issuccess(false);
    rsp.set_errmsg("Channel already exists");
    response = rsp.SerializeAsString();
    co_return;
  }
  // 创建频道
  auto channelId = redis_ptr->incr("global:channelid:count");
  protocol::common::channelInfo newChannelInfo;
  newChannelInfo.set_channelid(channelId);
  newChannelInfo.set_channelname(channelName);
  newChannelInfo.set_ownerid(stoll(sendPlayerId.value()));
  redis_ptr->set("channelName:" + channelName, std::to_string(channelId));
  redis_ptr->set("channelId:" + std::to_string(channelId), channelName);
  redis_ptr->set("channel:" + std::to_string(channelId),
                 newChannelInfo.SerializeAsString());
  redis_ptr->sadd("channel:member:" + std::to_string(channelId),
                  sendPlayerId.value());
  redis_ptr->sadd("channelSet", std::to_string(channelId));
  logger->info("Channel created successfully, channel name: {}", channelName);
  // 返回响应
  rsp.set_issuccess(true);
  rsp.set_allocated_sendplayer(new protocol::common::PlayerInfo(sendPlayer));
  rsp.add_channelinfo()->CopyFrom(newChannelInfo);
  protocol::ssmsg::SSMsgRsp ssMsgRsp;
  ssMsgRsp.set_msgtype(ssMsgReq.msgtype());
  ssMsgRsp.set_allocated_channelrsp(
      new protocol::sschannelmsg::SSChannelMsgRsp(rsp));
  response = ssMsgRsp.SerializeAsString();
  co_return;
}