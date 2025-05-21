#include "server.h"
#include "coroio/corochain.hpp"
#include "coroio/promises.hpp"
#include <coroio/all.hpp>
#include <coroutine>
#include <iostream>
#include <sys/socket.h>
#include <vector>

using namespace NNet;

void baseServer::wakeUpClientCoroutine(TEPoll::TSocket *socket) {
  if (!socket)
    return;
  auto it = clientCoroutines.find(socket->Fd());
  if (it != clientCoroutines.end()) {
    auto handle = std::move(it->second);
    clientCoroutines.erase(it);
    handle.resume();
  }
}

void baseServer::removeClientCoroutine(TEPoll::TSocket *socket) {
  if (!socket)
    return;
  clientCoroutines.erase(socket->Fd());
}

TVoidTask baseServer::client_handler(TEPoll::TSocket socket, int buffer_size) {
  std::vector<char> buffer(buffer_size);
  ssize_t size = 0;

  prepareSocket(socket);
  try {
    while (true) {
      auto readFuture = [&socket, &buffer, buffer_size]() -> TFuture<ssize_t> {
        co_return co_await socket.ReadSome(buffer.data(), buffer_size);
      }();
      auto outSideWakeUp = [this, &socket]() -> TFuture<ssize_t> {
        auto current = co_await Self{};
        int fd = socket.Fd();
        this->clientCoroutines[fd] = current;
        co_await std::suspend_always{};

        co_return -1;
      }();
      std::vector<TFuture<ssize_t>> futures;
      futures.push_back(std::move(readFuture));
      futures.push_back(std::move(outSideWakeUp));
      size = co_await Any(std::move(futures));

      if (size == -1) {
        continue;
      } else if (size == 0) {
        break; // 连接关闭;
      }
      std::string message(buffer.data(), size);
      std::string response;
      co_await handleMessage(socket, message, response);
      if (!response.empty()) {
        co_await socket.WriteSome(response.data(), response.size());
      }
    }
  } catch (const std::exception &ex) {
    std::cerr << "Exception: " << ex.what() << std::endl;
  }
  if (size == 0) {
    std::cerr << "Client disconnected" << std::endl;
  }
  co_return;
}

TVoidTask baseServer::start() {
  typename NNet::TEPoll::TSocket serverSocket(serverPoller,
                                              serverAddress.Domain());
  serverSocket.Bind(serverAddress);
  serverSocket.Listen();
  while (true) {
    auto clientSocket = co_await serverSocket.Accept();
    client_handler(std::move(clientSocket), bufferSize);
  }
  co_return;
}
