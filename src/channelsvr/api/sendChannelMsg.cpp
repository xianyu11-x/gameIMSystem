#include "sendChannelMsg.h"
#include "util/baseMsgHelper.h"
#include "util/sendMsg.h"
#include "util/config.hpp"

NNet::TFuture<std::string>
sendChannelMsg(NNet::TEPoll &poller, protocol::ssmsg::SSMsgReq &ssChannelMsg,
               protocol::common::MsgSender msgSender) {
  auto baseMsg = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                               msgSender, protocol::common::MsgBodyType::EN_REQ,
                               ssChannelMsg.SerializeAsString());
  auto& config = configManager::getInstance();
  std::string address = config.getChannelServerAddr(); // TODO::利用K8s获取目标地址
  auto baseMsgRspStr = co_await sendMsg(poller, address, baseMsg);
  auto baseMsgRsp = parseStringToBaseMsg(baseMsgRspStr);
  co_return baseMsgRsp.msgbody();
}