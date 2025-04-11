#include "coroio/epoll.hpp"
#include "util/server.h"
#include "coroio/all.hpp"
#include <functional>
#include <unordered_map>
#include <vector>
#include "common/BaseMsg.pb.h"
#include "gatesvr/CSMsg.pb.h"

#pragma once

class gateServer : public baseServer {
public:
    gateServer(NNet::TEPoll& poller,std::string address,int bufferSize);
    ~gateServer() override = default;
private:
    TVoidTask csLogin(const int socketFd,const std::string& message, std::string& response);
    


    void registerHandler();
    TVoidTask handleMessage(NNet::TEPoll::TSocket& socket,const std::string& message, std::string& response) override;
    void prepareSocket(NNet::TEPoll::TSocket& socket) override;
    void afterSocket(NNet::TEPoll::TSocket& socket) override{};
    std::unordered_map<std::string,NNet::TEPoll::TSocket*> activePlayers;
    std::unordered_map<int,NNet::TEPoll::TSocket*> connectedClients;

    using HandlerFunction = std::function<TVoidTask(const int socketFd,const std::string& message, std::string& response)>;
    std::unordered_map<protocol::csmsg::CSLoginMsgType, HandlerFunction> loginHandlerMap;
    std::unordered_map<protocol::csmsg::CSMsgType, HandlerFunction> csMsgHandlerMap;
};