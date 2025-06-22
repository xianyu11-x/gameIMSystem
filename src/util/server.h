#include "coroio/address.hpp"
#include "coroio/corochain.hpp"
#include "coroio/epoll.hpp"
#include "coroio/promises.hpp"
#include "coroio/socket.hpp"
#include <coroio/all.hpp>
#include <coroutine>
#include <queue>
#include <string>
#include <unordered_map>
#include <util/addressHelper.hpp>
#pragma once
using namespace NNet;

class baseServer {
public:
    baseServer(TUring& poller, std::string address, int bufferSize)
        : serverPoller(poller)
        , bufferSize(bufferSize)
    {
        auto [ip, port] = parseAddress(address);
        serverAddress = TAddress(ip, port);
        if (port == -1) {
            throw std::runtime_error("Invalid address");
        }
    };
    virtual ~baseServer() = default;

    // 子类需要实现的消息处理函数
    virtual TFuture<void> handleMessage(TUring::TSocket& socket, const std::string& message, std::string& response) = 0;

    // 建立连接后对Socket的预处理
    virtual void prepareSocket(TUring::TSocket& socket) = 0;

    virtual TFuture<void> afterSocket(TUring::TSocket& socket) = 0;

    TVoidTask client_handler(TUring::TSocket socket);

    TVoidTask ReadPacket(TUring::TSocket& socket, std::queue<std::string>& sendPackets);

    TVoidTask WritePacket(TUring::TSocket& socket, std::queue<std::string>& sendPackets);

    TFuture<std::string> pendSendMsg(int fd, const std::string& message,const std::string& msgId);

    void ResumeWriter(int fd);

    TVoidTask start();

    void wakeUpClientCoroutine(TUring::TSocket* socket);

    void removeClientCoroutine(TUring::TSocket* socket);
    // void run(int port,int buffer_size = 128);
    std::unordered_map<int, std::coroutine_handle<>> clientCoroutines;
    std::unordered_map<std::string, std::coroutine_handle<>> msgIdToCoroutineMap;
    std::unordered_map<std::string, std::string> msgIdToResponseMap;

    std::unordered_map<int, std::queue<std::string>> sendPacketsMap;
    std::unordered_map<int, std::coroutine_handle<>> sendPacketsCoroutineMap;

    TUring& serverPoller;
    TAddress serverAddress;
    int bufferSize;
};