#include "common/BaseMsg.pb.h"
#include "coroio/all.hpp"
#include "common/player.pb.h"
#pragma once
NNet::TFuture<std::string> sendLogoutMsg(NNet::TEPoll &poller,
    const protocol::common::PlayerInfo &playerInfo,protocol::common::MsgSender msgSender);