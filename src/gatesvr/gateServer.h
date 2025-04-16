#include "coroio/epoll.hpp"
#include "util/server.h"
#include "coroio/all.hpp"
#include <functional>
#include <memory>
#include <spdlog/logger.h>
#include <unordered_map>
#include <vector>
#include "common/BaseMsg.pb.h"
#include "gatesvr/CSMsg.pb.h"
#include "spdlog/sinks/basic_file_sink.h"
#include "spdlog/async.h"
#pragma once

class gateServer : public baseServer {
public:
    gateServer(NNet::TEPoll& poller,std::string address,int bufferSize);
    ~gateServer() override = default;
private:
    TFuture<void> csLogin(const int socketFd,const std::string& message, std::string& response);
    TFuture<void> csLogout(const int socketFd,const std::string& message, std::string& response);
    TFuture<void> loginMsgHandler(const int socketFd,const std::string& message, std::string& response);

    void registerHandler();
    TFuture<void> handleMessage(NNet::TEPoll::TSocket& socket,const std::string& message, std::string& response) override;
    void prepareSocket(NNet::TEPoll::TSocket& socket) override;
    void afterSocket(NNet::TEPoll::TSocket& socket) override{};
    std::unordered_map<std::string,NNet::TEPoll::TSocket*> activePlayers;
    std::unordered_map<int64_t,std::string> playerIdToPlayerName;
    std::unordered_map<int,NNet::TEPoll::TSocket*> connectedClients;

    using HandlerFunction = std::function<TFuture<void>(const int socketFd,const std::string& message, std::string& response)>;
    std::unordered_map<protocol::csmsg::CSLoginMsgType, HandlerFunction> loginHandlerMap;
    std::unordered_map<protocol::csmsg::CSMsgType, HandlerFunction> csMsgHandlerMap;

    std::shared_ptr<spdlog::logger> logger;
};