#include "channelsvr/channelServer.h"
#include "coroio/corochain.hpp"

TFuture<void> channelServer::ssPullChannelList(const int socketFd,
                                               const std::string &message,
                                               std::string &response) {
  protocol::ssmsg::SSMsgReq ssMsgReq;
  ssMsgReq.ParseFromString(message);
  auto req = ssMsgReq.channelreq();
  protocol::sschannelmsg::SSChannelMsgRsp rsp;
  rsp.set_msgtype(req.msgtype());

  // 用户合法性校验
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
  // 获取频道列表
  std::vector<std::string> channelList;
  redis_ptr->smembers("channelSet", std::back_inserter(channelList));
  logger->info("Pull channel list success, player name: {}", sendPlayerName);
  for (const auto &channelId : channelList) {
    auto channelInfoStr = redis_ptr->get("channel:" + channelId);
    if (channelInfoStr) {
      protocol::common::channelInfo channelInfo;
      channelInfo.ParseFromString(channelInfoStr.value());
      rsp.add_channelinfo()->CopyFrom(channelInfo);
    }
  }

  rsp.set_issuccess(true);
  rsp.set_allocated_sendplayer(new protocol::common::PlayerInfo(sendPlayer));
  protocol::ssmsg::SSMsgRsp ssMsgRsp;
  ssMsgRsp.set_msgtype(ssMsgReq.msgtype());
  ssMsgRsp.set_allocated_channelrsp(
      new protocol::sschannelmsg::SSChannelMsgRsp(rsp));
  response = ssMsgRsp.SerializeAsString();
  co_return;
}