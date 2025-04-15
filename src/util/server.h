#include "coroio/address.hpp"
#include "coroio/corochain.hpp"
#include "coroio/epoll.hpp"
#include "coroio/promises.hpp"
#include <coroio/all.hpp>
#include <string>
#include <util/addressHelper.hpp>
#pragma once
using namespace NNet;

class baseServer {
public:
    baseServer(TEPoll& poller,std::string address,int bufferSize): serverPoller(poller),bufferSize(bufferSize) {
        auto [ip,port] = parseAddress(address);
        serverAddress = TAddress(ip,port);
        if (port == -1) {
            throw std::runtime_error("Invalid address");
        }
    };
    virtual ~baseServer() = default;

    // 子类需要实现的消息处理函数
    virtual TFuture<void> handleMessage(TEPoll::TSocket& socket,const std::string& message, std::string& response)=0;

    //建立连接后对Socket的预处理
    virtual void prepareSocket(TEPoll::TSocket& socket)=0;

    virtual void afterSocket(TEPoll::TSocket& socket)=0;

    TVoidTask client_handler(TEPoll::TSocket socket,int buffer_size);

    TVoidTask start();

    //void run(int port,int buffer_size = 128);

    TEPoll& serverPoller;
    TAddress serverAddress;
    int bufferSize;
};