#include "coroio/all.hpp"
#include <string>
#include "coroio/epoll.hpp"
#include "util/addressHelper.hpp"
#pragma once
NNet::TFuture<std::string> sendMsg(NNet::TEPoll &poller,const std::string& address,const std::string& message);