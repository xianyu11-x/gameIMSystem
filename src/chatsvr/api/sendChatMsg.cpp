#include "sendChatMsg.h"
#include "common/SSMsg.pb.h"
#include "util/baseMsgHelper.h"
#include "util/sendMsg.h"
NNet::TFuture<std::string>
sendChatMsg(NNet::TEPoll &poller, protocol::ssmsg::SSMsgReq &ssChatMsg,
            protocol::common::MsgSender msgSender) {
  auto baseMsg = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                               msgSender, protocol::common::MsgBodyType::EN_REQ,
                               ssChatMsg.SerializeAsString());
  std::string address = "127.0.0.1:10002"; // TODO::利用K8s获取目标地址
  auto baseMsgRspStr = co_await sendMsg(poller, address, baseMsg);
  auto baseMsgRsp = parseStringToBaseMsg(baseMsgRspStr);
  co_return baseMsgRsp.msgbody();
}