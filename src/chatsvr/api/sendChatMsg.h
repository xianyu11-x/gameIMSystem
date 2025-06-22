#include "chatsvr/SSChatMsg.pb.h"
#include "common/BaseMsg.pb.h"
#include "coroio/all.hpp"
#include "common/SSMsg.pb.h"

NNet::TFuture<std::string> sendChatMsg(NNet::TUring &poller,
                                        protocol::ssmsg::SSMsgReq &ssChatMsg,protocol::common::MsgSender msgSender);