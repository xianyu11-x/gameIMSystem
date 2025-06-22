#include "sendChatMsg.h"
#include "common/SSMsg.pb.h"
#include "util/baseMsgHelper.h"
#include "util/sendMsg.h"
#include "util/config.hpp"
NNet::TFuture<std::string>
sendChatMsg(NNet::TUring &poller, protocol::ssmsg::SSMsgReq &ssChatMsg,
            protocol::common::MsgSender msgSender) {
  auto [baseMsg,msgId] = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                               msgSender, protocol::common::MsgBodyType::EN_REQ,
                               ssChatMsg.SerializeAsString());
  auto& config = configManager::getInstance();
  std::string address = config.getChatServerAddr(); // TODO::利用K8s获取目标地址
  auto baseMsgRspStr = co_await sendMsg(poller, address, baseMsg);
  auto baseMsgRsp = parseStringToBaseMsg(baseMsgRspStr);
  co_return baseMsgRsp.msgbody();
}