#include "baseMsgHelper.h"
#include "util/uuid.hpp"
#include <string>

protocol::common::baseMsg parseStringToBaseMsg(const std::string& str) {
    protocol::common::baseMsg msg;
    if (!msg.ParseFromString(str)) {
        throw std::runtime_error("Failed to parse baseMsg from string");
    }
    return msg;
}

std::pair<std::string,std::string> createBaseMsg(protocol::common::MsgType msgType,
                          protocol::common::MsgSender msgSender,
                          protocol::common::MsgBodyType msgBodyType,
                          const std::string& msgBody,const std::string& reqMsgId) {
    protocol::common::baseMsg msg;
    protocol::common::MsgInfo* msgInfo = msg.mutable_msginfo();
    msgInfo->set_msgtype(msgType);
    msgInfo->set_msgsender(msgSender);
    msgInfo->set_msgbodytype(msgBodyType);
    std::string msgId;
    if(msgBodyType == protocol::common::MsgBodyType::EN_RSP ) {
        if(!reqMsgId.empty()) {
            msgInfo->set_msgid(reqMsgId);
            msgId = reqMsgId;
        }
        else throw std::runtime_error("Rsponse message must have same request ID");
    } else {
        msgId = generateUUID();
        msgInfo->set_msgid(msgId);
    }
    msg.set_msgbody(msgBody);
    
    std::string output;
    if (!msg.SerializeToString(&output)) {
        throw std::runtime_error("Failed to serialize baseMsg to string");
    }
    return {output, msgId};
}