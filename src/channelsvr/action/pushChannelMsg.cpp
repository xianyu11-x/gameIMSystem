#include "channelsvr/channelServer.h"
#include "common/SSMsg.pb.h"
#include "common/player.pb.h"
#include "coroio/promises.hpp"
#include "util/baseMsgHelper.h"
#include "util/sendMsg.h"
#include "util/config.hpp"
#include <unordered_set>
TVoidTask channelServer::ssPushChannelMsg(
    std::unordered_set<std::string> members,
    protocol::common::channelInfo channelInfo,
    protocol::common::PlayerInfo sendPlayer,
    std::vector<protocol::common::chatMessage> channelChatMessageList,
    protocol::common::MsgSender msgSender) {
  protocol::sschannelmsg::SSChannelMsgReq ssChannelMsg;
  ssChannelMsg.set_msgtype(
      protocol::sschannelmsg::SSChannelMsgType::EN_RECEIVE);
  ssChannelMsg.set_allocated_sendplayer(
      new protocol::common::PlayerInfo(sendPlayer));
  auto channelInfoPtr = ssChannelMsg.mutable_channelinfo();
  channelInfoPtr->set_channelid(channelInfo.channelid());
  channelInfoPtr->set_channelname(channelInfo.channelname());
  channelInfoPtr->set_ownerid(channelInfo.ownerid());
  // 设置广播成员列表
  for (const auto &member : members) {
    protocol::common::PlayerInfo playerInfo;
    playerInfo.set_playerid(stol(member));
    channelInfoPtr->add_members()->CopyFrom(playerInfo);
  }

  for (const auto &chatMessage : channelChatMessageList) {
    ssChannelMsg.add_chatmessage()->CopyFrom(chatMessage);
  }
  protocol::ssmsg::SSMsgReq ssMsgReq;
  ssMsgReq.set_msgtype(protocol::ssmsg::SSMsgType::EN_CHANNEL);
  ssMsgReq.set_allocated_channelreq(
      new protocol::sschannelmsg::SSChannelMsgReq(ssChannelMsg));

  auto baseMsg = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                               msgSender, protocol::common::MsgBodyType::EN_REQ,
                               ssMsgReq.SerializeAsString());                
  auto& config = configManager::getInstance();
  std::string address = config.getGateServerAddr();
  auto baseMsgRspStr = co_await sendMsg(serverPoller, address, baseMsg);
  auto baseMsgRsp = parseStringToBaseMsg(baseMsgRspStr);
  auto ssMsgRspStr = baseMsgRsp.msgbody();
  protocol::ssmsg::SSMsgRsp ssMsgRsp;
  ssMsgRsp.ParseFromString(ssMsgRspStr);
  if (ssMsgRsp.channelrsp().issuccess()) {
    logger->info(
        "Push channel message success, channel name: {}, send player: {}",
        channelInfo.channelname(), sendPlayer.playername());
  } else {
    logger->error(
        "Push channel message failed: {}, channel name: {}, send player: {}",
        ssMsgRsp.channelrsp().errmsg(), channelInfo.channelname(),
        sendPlayer.playername());
  }
  co_return;
}