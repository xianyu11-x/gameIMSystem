#include "sendLogoutMsg.h"
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "common/player.pb.h"
#include "util/baseMsgHelper.h"
#include "util/sendMsg.h"

NNet::TFuture<std::string>
sendLogoutMsg(NNet::TEPoll &poller,
              const protocol::common::PlayerInfo &playerInfo,
              protocol::common::MsgSender msgSender) {
  protocol::ssmsg::SSMsgReq req;
  req.set_msgtype(protocol::ssmsg::SSMsgType::EN_LOGIN);
  auto loginReq = req.mutable_loginreq();
  loginReq->set_msgtype(protocol::ssloginmsg::SSLoginMsgType::EN_PLAYER_LOGOUT);
  auto loginPlayer = loginReq->mutable_playerinfo();
  loginPlayer->set_playername(playerInfo.playername());
  loginPlayer->set_playerid(playerInfo.playerid());
  loginPlayer->set_playertoken(playerInfo.playertoken());
  auto baseMsg = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                               msgSender, protocol::common::MsgBodyType::EN_REQ,
                               req.SerializeAsString());
  std::string address = "127.0.0.1:10001";
  auto baseMsgRspStr = co_await sendMsg(poller, address, baseMsg);
  auto baseMsgRsp = parseStringToBaseMsg(baseMsgRspStr);
  co_return baseMsgRsp.msgbody();
}