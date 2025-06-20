#include "sendMsg.h"
#include "coroio/address.hpp"
#include "coroio/corochain.hpp"
#include "coroio/epoll.hpp"
#include "util/addressHelper.hpp"

static bool isValidIP(const std::string &ip) {
  struct sockaddr_in sa;
  return inet_pton(AF_INET, ip.c_str(), &(sa.sin_addr)) != 0;
}

NNet::TFuture<std::string> sendMsg(NNet::TEPoll &poller,
                                   const std::string &address,
                                   const std::string &message) {
  static constexpr int maxLineSize = 4096;
  auto [ip, port] = parseAddress(address);
  //std::cout<< "sendMsg: ip="<<ip<<" port="<<port<<std::endl;
  NNet::TAddress addr;
  if (!isValidIP(ip)) {
    addr = NNet::TAddress{resolveAddress(ip), port};
  }else{
    addr = NNet::TAddress{ip, port};
  }
  NNet::TEPoll::TSocket socket{poller, addr.Domain()};
  co_await socket.Connect(addr, NNet::TClock::now() +
                                    std::chrono::milliseconds(1000));
  co_await socket.WriteSome(message.data(), message.size());
  std::string response;
  std::vector<char> in(maxLineSize);
  size_t size = co_await socket.ReadSome(in.data(), in.size());
  if (size > 0) {
    response.assign(in.data(), size);
  }
  co_return response;
}

NNet::TFuture<std::string> sendMsg(NNet::TSocket *socket,
                                   const std::string &message) {
  co_await socket->WriteSome(message.data(), message.size());
  std::string response;
  std::vector<char> in(4096);
  size_t size = co_await socket->ReadSome(in.data(), in.size());
  if (size > 0) {
    response.assign(in.data(), size);
  }
  co_return response;
}