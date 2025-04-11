#include "baseMsgHelper.h"

protocol::common::baseMsg parseStringToBaseMsg(const std::string& str) {
    protocol::common::baseMsg msg;
    if (!msg.ParseFromString(str)) {
        throw std::runtime_error("Failed to parse baseMsg from string");
    }
    return msg;
}

std::string createBaseMsg(protocol::common::MsgType msgType,
                          protocol::common::MsgSender msgSender,
                          protocol::common::MsgBodyType msgBodyType,
                          const std::string& msgBody) {
    protocol::common::baseMsg msg;
    protocol::common::MsgInfo* msgInfo = msg.mutable_msginfo();
    msgInfo->set_msgtype(msgType);
    msgInfo->set_msgsender(msgSender);
    msgInfo->set_msgbodytype(msgBodyType);
    msg.set_msgbody(msgBody);
    
    std::string output;
    if (!msg.SerializeToString(&output)) {
        throw std::runtime_error("Failed to serialize baseMsg to string");
    }
    return output;
}