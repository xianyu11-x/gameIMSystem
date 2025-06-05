#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "coroio/all.hpp"
#include "coroio/corochain.hpp"
#include "coroio/epoll.hpp"
#include "spdlog/logger.h"
#include "util/server.h"
#include "channelsvr/SSChannelMsg.pb.h"
#include <functional>
#include <string>
#include <sw/redis++/redis++.h>
#include <unordered_map>
#include <vector>
#pragma once

class channelServer : public baseServer {
public:
    channelServer(NNet::TEPoll& poller, std::string address, int bufferSize);
    ~channelServer() override = default;

private:
    TFuture<void> ssPullChannelList(const int socketFd, const std::string& message, std::string& response);
    TFuture<void> ssPullChannelHistory(const int socketFd, const std::string& message, std::string& response);
    TFuture<void> ssSendChannelMsg(const int socketFd, const std::string& message, std::string& response);
    TFuture<void> ssLeaveChannel(const int socketFd, const std::string& message, std::string& response);
    TFuture<void> ssJoinChannel(const int socketFd, const std::string& message, std::string& response);
    TFuture<void> ssCreateChannel(const int socketFd, const std::string& message, std::string& response);
    TFuture<void> ssDestroyChannel(const int socketFd, const std::string& message, std::string& response);
    TFuture<void> channelHandler(const int socketFd, const std::string& message, std::string& response);

    void registerHandler();
    TFuture<void> handleMessage(NNet::TEPoll::TSocket& socket, const std::string& message, std::string& response) override;
    void prepareSocket(NNet::TEPoll::TSocket& socket) override;
    TFuture<void> afterSocket(NNet::TEPoll::TSocket& socket) override { co_return; };

    using HandlerFunction = std::function<TFuture<void>(const int socketFd, const std::string& message, std::string& response)>;
    std::unordered_map<protocol::sschannelmsg::SSChannelMsgType, HandlerFunction> channelHandlerMap;
    std::unordered_map<protocol::ssmsg::SSMsgType, HandlerFunction> ssMsgHandlerMap;

    std::unique_ptr<sw::redis::Redis> redis_ptr;
    std::shared_ptr<spdlog::logger> logger;
};