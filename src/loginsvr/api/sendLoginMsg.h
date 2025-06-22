#include "common/BaseMsg.pb.h"
#include "coroio/all.hpp"

NNet::TFuture<std::string> sendLoginMsg(NNet::TUring &poller,
                                        const std::string &playerName,protocol::common::MsgSender msgSender);