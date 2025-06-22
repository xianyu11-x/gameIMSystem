#include "server.h"
#include "coroio/corochain.hpp"
#include "coroio/promises.hpp"
#include <coroio/all.hpp>
#include <coroutine>
#include <iostream>
#include <queue>
#include <string>
#include <sys/socket.h>
#include <vector>

using namespace NNet;

void baseServer::wakeUpClientCoroutine(TUring::TSocket* socket)
{
    if (!socket)
        return;
    auto it = clientCoroutines.find(socket->Fd());
    if (it != clientCoroutines.end()) {
        auto handle = std::move(it->second);
        clientCoroutines.erase(it);
        handle.resume();
    }
}

void baseServer::removeClientCoroutine(TUring::TSocket* socket)
{
    if (!socket)
        return;
    clientCoroutines.erase(socket->Fd());
}

TVoidTask baseServer::ReadPacket(TUring::TSocket& socket, std::queue<std::string>& sendPackets)
{
    std::vector<char> buffer(bufferSize);
    ssize_t size = 0;
    try {
        while (true) {
            ssize_t size = co_await socket.ReadSome(buffer.data(), bufferSize);
            if (size <= 0) {
                break; // 连接关闭
            }
            std::string message(buffer.data(), size);
            std::string response;
            co_await handleMessage(socket, message, response);
            if (!response.empty()) {
                sendPackets.push(response);
                ResumeWriter(socket.Fd());
            }
        }
    } catch (const std::exception& ex) {
        std::cerr << "Exception in ReadPacket: " << ex.what() << std::endl;
    }
    // if (size == 0) {
    //     std::cerr << "Client disconnected" << std::endl;
    // }
    wakeUpClientCoroutine(&socket);
    co_return;
}

TVoidTask baseServer::WritePacket(TUring::TSocket& socket, std::queue<std::string>& sendPackets)
{
    while (true) {
        while (sendPackets.empty()) {
            sendPacketsCoroutineMap[socket.Fd()] = co_await Self();
            co_await std::suspend_always {};
        }
        sendPacketsCoroutineMap[socket.Fd()] = {};
        std::string rsp = sendPackets.front();
        sendPackets.pop();
        co_await socket.WriteSome(rsp.data(), rsp.size());
    }
    co_return;
}

void baseServer::ResumeWriter(int fd)
{
    if(sendPacketsCoroutineMap.find(fd) != sendPacketsCoroutineMap.end() && sendPacketsCoroutineMap[fd]) {
      sendPacketsCoroutineMap[fd].resume();
    }
}

TVoidTask baseServer::client_handler(TUring::TSocket socket)
{

    ssize_t size = 0;
    sendPacketsMap[socket.Fd()] = std::queue<std::string>();
    prepareSocket(socket);
    ReadPacket(socket, sendPacketsMap[socket.Fd()]);
    WritePacket(socket, sendPacketsMap[socket.Fd()]);
    auto current = co_await Self {};
    int fd = socket.Fd();
    clientCoroutines[fd] = current;
    co_await std::suspend_always {};
    std::cout << "Client disconnected, fd: " << socket.Fd() << std::endl;
    co_await afterSocket(socket);
    co_return;
}

TFuture<std::string> baseServer::pendSendMsg(int fd, const std::string& message,const std::string& msgId)
{
    if(msgId == "") {
        std::cerr << "Message ID cannot be empty" << std::endl;
        throw std::runtime_error("Message ID cannot be empty");
    }
    if (sendPacketsMap.find(fd) == sendPacketsMap.end()) {
        sendPacketsMap[fd] = std::queue<std::string>();
    }
    sendPacketsMap[fd].push(message);
    ResumeWriter(fd);
    auto handle = co_await Self();
    msgIdToCoroutineMap[msgId] = handle;
    co_await std::suspend_always {};
    auto it = msgIdToResponseMap.find(msgId);
    std::string response;
    if (it != msgIdToResponseMap.end()) {
        response = it->second;
        msgIdToResponseMap.erase(it);
    } else {
        std::cerr << "No response found for message ID: " << msgId << std::endl;
    }
    co_return response;
}

TVoidTask baseServer::start()
{
    typename NNet::TUring::TSocket serverSocket(serverPoller,
        serverAddress.Domain());
    serverSocket.Bind(serverAddress);
    serverSocket.Listen();
    while (true) {
        auto clientSocket = co_await serverSocket.Accept();
        client_handler(std::move(clientSocket));
    }
    co_return;
}
