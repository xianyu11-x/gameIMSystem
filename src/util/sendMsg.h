#include "coroio/address.hpp"
#include "coroio/all.hpp"
#include <string>
#include "coroio/corochain.hpp"
#include "coroio/epoll.hpp"
#include "coroio/socket.hpp"
#include "util/addressHelper.hpp"
#pragma once
NNet::TFuture<std::string> sendMsg(NNet::TEPoll &poller,const std::string& address,const std::string& message);

NNet::TFuture<std::string> sendMsg(NNet::TSocket* socket, const std::string &message);