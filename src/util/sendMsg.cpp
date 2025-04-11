#include "sendMsg.h"
#include "coroio/address.hpp"
#include "coroio/epoll.hpp"

NNet::TFuture<std::string> sendMsg(NNet::TEPoll &poller,const std::string& address,const std::string& message){
    static constexpr int maxLineSize = 4096;
    auto [ip,port] = parseAddress(address);
    NNet::TAddress addr(ip,port);
    NNet::TEPoll::TSocket socket{poller,addr.Domain()};
    co_await socket.Connect(addr, NNet::TClock::now()+std::chrono::milliseconds(1000));
    co_await socket.WriteSome(message.data(), message.size());
    std::string response;
    std::vector<char> in(maxLineSize);
    size_t size = co_await socket.ReadSome(in.data(), in.size());
    if (size > 0) {
        response.assign(in.data(), size);
    }
    co_return response;
}