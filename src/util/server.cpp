#include "server.h"
#include "coroio/promises.hpp"
#include <coroio/all.hpp>
#include <iostream>
#include <sys/socket.h>
#include <vector>

using namespace NNet;

TVoidTask baseServer::client_handler(TEPoll::TSocket socket,int buffer_size){
    std::vector<char> buffer(buffer_size);
    ssize_t size = 0;
    prepareSocket(socket);
    try {
      while ((size = co_await socket.ReadSome(buffer.data(),
                                                    buffer_size)) > 0) {
        std::string message(buffer.data(), size);
        std::string response;
        handleMessage(socket,message, response);
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
  typename NNet::TEPoll::TSocket serverSocket(serverPoller, serverAddress.Domain());
  serverSocket.Bind(serverAddress);
  serverSocket.Listen();
  while (true) {
    auto clientSocket = co_await serverSocket.Accept();
    client_handler(std::move(clientSocket), bufferSize);
  }
  co_return;
}

