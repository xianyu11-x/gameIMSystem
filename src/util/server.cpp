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

// void baseServer::wakeUpClientCoroutine(TUring::TSocket* socket)
// {
//     if (!socket)
//         return;
//     auto it = clientCoroutines.find(socket->Fd());
//     if (it != clientCoroutines.end()) {
//         auto handle = std::move(it->second);
//         clientCoroutines.erase(it);
//         handle.resume();
//     }
// }

// void baseServer::removeClientCoroutine(TUring::TSocket* socket)
// {
//     if (!socket)
//         return;
//     clientCoroutines.erase(socket->Fd());
// }

TFuture<void> baseServer::ReadPacket(TUring::TSocket& socket, std::queue<std::string>& sendPackets)
{
    int fd = socket.Fd();
    clientStates[fd].readPacketActive = true;
    std::vector<char> buffer(bufferSize);
    ssize_t size = 0;
    try {
        while (true) {
            if (clientStates[fd].cleanupRequested) {
                break;
            }
            ssize_t size = co_await socket.ReadSome(buffer.data(), bufferSize);
            if (size <= 0) {
                clientStates[fd].cleanupRequested = true;
                ResumeWriter(fd);
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
        clientStates[fd].cleanupRequested = true;
        clientStates[fd].readPacketActive = false;
        // ResumeWriter(fd);
        throw;
    }
    // if (size == 0) {
    //     std::cerr << "Client disconnected" << std::endl;
    // }
    clientStates[fd].readPacketActive = false;
    co_return;
}

TFuture<void> baseServer::WritePacket(TUring::TSocket& socket, std::queue<std::string>& sendPackets)
{
    int fd = socket.Fd();
    clientStates[fd].writePacketActive = true;
    try {
        while (true) {
            while (sendPackets.empty()) {
                if (clientStates[fd].cleanupRequested) {
                    break;
                }
                sendPacketsCoroutineMap[socket.Fd()] = co_await Self();
                co_await std::suspend_always {};
            }
            sendPacketsCoroutineMap[socket.Fd()] = {};
            if (clientStates[fd].cleanupRequested || sendPacketsMap.find(socket.Fd()) == sendPacketsMap.end())
                break;
            std::string rsp = sendPackets.front();
            sendPackets.pop();
            co_await socket.WriteSome(rsp.data(), rsp.size());
        }
    } catch (const std::exception& ex) {
        std::cerr << "Exception in WritePacket: " << ex.what() << std::endl;
        clientStates[fd].cleanupRequested = true;
        clientStates[fd].writePacketActive = false;
        throw;
    }
    clientStates[fd].writePacketActive = false;
    co_return;
}

void baseServer::checkAndWakeupClientHandler(int fd)
{
}

void baseServer::cleanupResource(int fd)
{
    try {
        // serverPoller.Cancel(fd);
        serverPoller.RemoveEvent(fd);
    } catch (...) {
        // 忽略取消异常
    }
    // co_await serverPoller.Sleep(std::chrono::microseconds(0));
    if (sendPacketsCoroutineMap.find(fd) != sendPacketsCoroutineMap.end()) {
        sendPacketsCoroutineMap.erase(fd);
    }
    if (sendPacketsMap.find(fd) != sendPacketsMap.end()) {
        sendPacketsMap.erase(fd);
    }
    if (clientStates.count(fd)) {
        auto owned_msg_ids_copy = clientStates.at(fd).ownedMsgIds;
        for (const auto& msgId : owned_msg_ids_copy) {
            std::coroutine_handle<> handle_to_resume;
            {
                std::lock_guard<std::mutex> lock(msgIdMapMutex);
                auto it = msgIdToCoroutineMap.find(msgId);
                if (it != msgIdToCoroutineMap.end()) {
                     handle_to_resume = std::move(it->second);
                    msgIdToCoroutineMap.erase(it);
                    msgIdToResponseMap.erase(msgId);
                }
            }
            if(handle_to_resume) {
                handle_to_resume.resume();
            }
        }
    }
}

void baseServer::ResumeWriter(int fd)
{
    if (sendPacketsCoroutineMap.find(fd) != sendPacketsCoroutineMap.end() && sendPacketsCoroutineMap[fd]) {
        sendPacketsCoroutineMap[fd].resume();
    }
}

TVoidTask baseServer::client_handler(TUring::TSocket socket)
{

    ssize_t size = 0;
    int fd = socket.Fd();
    sendPacketsMap[socket.Fd()] = std::queue<std::string>();
    clientStates[socket.Fd()] = ClientState {};
    prepareSocket(socket);

    auto readTask = ReadPacket(socket, sendPacketsMap[socket.Fd()]);
    auto writeTask = WritePacket(socket, sendPacketsMap[socket.Fd()]);
    try {
        co_await readTask;
    } catch (const std::exception& ex) {
        std::cerr << "Exception in client_handler: " << ex.what() << std::endl;
    }
    std::cout << "Client disconnected, fd: " << fd << std::endl;
    clientStates[fd].cleanupRequested = true;
    ResumeWriter(fd);
    // try {
    //     serverPoller.Cancel(fd);
    // } catch (...) {
    // }
    try {
        co_await writeTask;
    } catch (const std::exception& ex) {
        // 这是预期的，如果任务在I/O操作中被取消。
        std::cerr << "Exception after writeTask: " << ex.what() << std::endl;
    }
    // co_await afterSocket(socket);
    cleanupResource(fd);
    co_return;
}

TFuture<std::string> baseServer::pendSendMsg(int fd, const std::string& message, const std::string& msgId)
{
    if (msgId == "") {
        std::cerr << "Message ID cannot be empty" << std::endl;
        throw std::runtime_error("Message ID cannot be empty");
    }
    if (clientStates.count(fd)) {
        clientStates.at(fd).ownedMsgIds.insert(msgId);
    }
    if (sendPacketsMap.find(fd) == sendPacketsMap.end()) {
        std::cerr << "No send packets map found for fd: " << fd << std::endl;
        co_return std::string {};
    }
    sendPacketsMap[fd].push(message);
    ResumeWriter(fd);
    auto handle = co_await Self();
    {
        std::lock_guard<std::mutex> lock(msgIdMapMutex);
        msgIdToCoroutineMap[msgId] = handle;
    }
    co_await std::suspend_always {};
    std::string response {};
    {
        std::lock_guard<std::mutex> lock(msgIdMapMutex);
        auto it = msgIdToResponseMap.find(msgId);
        if (it != msgIdToResponseMap.end()) {
            response = it->second;
            msgIdToResponseMap.erase(it);
        } else {
            std::cerr << "No response found for message ID: " << msgId << std::endl;
        }
    }
    if (clientStates.count(fd)) {
        clientStates[fd].ownedMsgIds.erase(msgId);
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
