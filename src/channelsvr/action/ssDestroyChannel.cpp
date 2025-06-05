#include "channelsvr/channelServer.h"
#include "common/channel.pb.h"
#include "coroio/corochain.hpp"

TFuture<void> channelServer::ssDestroyChannel(const int socketFd,
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
    logger->error("Channel not found, channel id: {}", channelId.value());
    rsp.set_issuccess(false);
    rsp.set_errmsg("Channel not found");
    response = rsp.SerializeAsString();
    co_return;
  }

  // 检查发送者是否是频道的所有者
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

  if (channelInfo.ownerid() != stoll(sendPlayerId.value())) {
    logger->error("Only the owner can destroy the channel, player name: {}, "
                  "channel id: {}",
                  sendPlayerName, channelId.value());
    rsp.set_issuccess(false);
    rsp.set_errmsg("Only the owner can destroy the channel");
    response = rsp.SerializeAsString();
    co_return;
  }

  // 删除频道
  redis_ptr->del("channelName:" + channelName);
  redis_ptr->del("channelId:" + channelId.value());
  redis_ptr->del("channel:" + channelId.value());
  redis_ptr->srem("channelSet", channelId.value());
  redis_ptr->del("channel:member:" + channelId.value());

  logger->info("Channel destroyed successfully, channel name: {}", channelName);

  // 返回响应
  rsp.set_issuccess(true);
  rsp.set_allocated_sendplayer(new protocol::common::PlayerInfo(sendPlayer));
  response = rsp.SerializeAsString();
  co_return;
}