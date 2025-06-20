#include "sendLoginMsg.h"
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "util/baseMsgHelper.h"
#include "util/sendMsg.h"
#include "util/config.hpp"

NNet::TFuture<std::string> sendLoginMsg(NNet::TEPoll &poller,
                                        const std::string &playerName,protocol::common::MsgSender msgSender) {
  protocol::ssmsg::SSMsgReq req;
  req.set_msgtype(protocol::ssmsg::SSMsgType::EN_LOGIN);
  auto loginreq = req.mutable_loginreq();
  loginreq->set_msgtype(protocol::ssloginmsg::SSLoginMsgType::EN_PLAYER_LOGIN);
  auto loginPlayer = loginreq->mutable_playerinfo();
  loginPlayer->set_playername(playerName);
  auto [baseMsg,msgId] = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,msgSender, protocol::common::MsgBodyType::EN_REQ, req.SerializeAsString());
  auto& config = configManager::getInstance();
  std::string address = config.getLoginServerAddr(); //TODO::利用K8s获取目标地址
  auto baseMsgRspStr = co_await sendMsg(poller, address, baseMsg);
  auto baseMsgRsp = parseStringToBaseMsg(baseMsgRspStr);
  co_return baseMsgRsp.msgbody();
}