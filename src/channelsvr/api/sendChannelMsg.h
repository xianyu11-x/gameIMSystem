#include "chatsvr/SSChatMsg.pb.h"
#include "common/BaseMsg.pb.h"
#include "coroio/all.hpp"
#include "common/SSMsg.pb.h"

NNet::TFuture<std::string> sendChannelMsg(NNet::TUring &poller,
                                        protocol::ssmsg::SSMsgReq &ssChannelMsg,protocol::common::MsgSender msgSender);