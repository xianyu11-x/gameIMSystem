#include "coroio/corochain.hpp"
#include "coroio/epoll.hpp"
#include "util/server.h"
#include "coroio/all.hpp"
#include <functional>
#include <unordered_map>
#include <vector>
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "spdlog/logger.h"
#include <sw/redis++/redis++.h>
#pragma once

class loginServer : public baseServer {
public:
    loginServer(NNet::TEPoll& poller,std::string address,int bufferSize);
    ~loginServer() override = default;
private:
    TFuture<void> ssLogin(const int socketFd,const std::string& message, std::string& response);
    TFuture<void> ssLogout(const int socketFd,const std::string& message, std::string& response);
    TFuture<void> loginMsgHandler(const int socketFd,const std::string& message, std::string& response);

    void registerHandler();
    TFuture<void> handleMessage(NNet::TEPoll::TSocket& socket,const std::string& message, std::string& response) override;
    void prepareSocket(NNet::TEPoll::TSocket& socket) override;
    void afterSocket(NNet::TEPoll::TSocket& socket) override{};


    using HandlerFunction = std::function<TFuture<void>(const int socketFd,const std::string& message, std::string& response)>;
    std::unordered_map<protocol::ssloginmsg::SSLoginMsgType, HandlerFunction> loginHandlerMap;
    std::unordered_map<protocol::ssmsg::SSMsgType, HandlerFunction> ssMsgHandlerMap;

    std::unique_ptr<sw::redis::Redis> redis_ptr;
    std::shared_ptr<spdlog::logger> logger;
};