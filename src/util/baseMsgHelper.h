#include "common/BaseMsg.pb.h"
#pragma once

protocol::common::baseMsg parseStringToBaseMsg(const std::string& str); 

std::pair<std::string,std::string> createBaseMsg(protocol::common::MsgType msgType,
                          protocol::common::MsgSender msgSender,
                          protocol::common::MsgBodyType msgBodyType,
                          const std::string& msgBody,const std::string& reqMsgId = ""); 