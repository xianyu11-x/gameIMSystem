#include "coroio/address.hpp"
#include "coroio/all.hpp"
#include <string>
#include "coroio/corochain.hpp"
#include "coroio/epoll.hpp"
#include "coroio/socket.hpp"
#include "util/addressHelper.hpp"
#pragma once
NNet::TFuture<std::string> sendMsg(NNet::TUring &poller,const std::string& address,const std::string& message);

