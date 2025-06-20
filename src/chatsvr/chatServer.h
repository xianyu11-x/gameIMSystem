#include "chatsvr/SSChatMsg.pb.h"
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "coroio/all.hpp"
#include "coroio/corochain.hpp"
#include "coroio/epoll.hpp"
#include "spdlog/logger.h"
#include "util/server.h"
#include <functional>
#include <sw/redis++/redis++.h>
#include <unordered_map>
#include <vector>
#pragma once

class chatServer : public baseServer {
public:
  chatServer(NNet::TEPoll &poller, std::string address, int bufferSize);
  ~chatServer() override = default;

private:
  TFuture<void> ssSendChatMsg(const int socketFd, const std::string &message,
                              std::string &response);
  TFuture<void> ssPullHistoryChatMsg(const int socketFd,
                                     const std::string &message,
                                     std::string &response);
  TFuture<void> chatMsgHandler(const int socketFd, const std::string msgId ,const std::string &message,
                               std::string &response);

  TVoidTask ssPushMsg(const protocol::sschatmsg::SSChatMsgReq ssChatMsg,
                      protocol::common::MsgSender msgSender, int expectAck);

  void registerHandler();
  TFuture<void> handleMessage(NNet::TEPoll::TSocket &socket,
                              const std::string &message,
                              std::string &response) override;
  void prepareSocket(NNet::TEPoll::TSocket &socket) override {};
  TFuture<void> afterSocket(NNet::TEPoll::TSocket &socket) override {
    co_return;
  };

  using HandlerFunction = std::function<TFuture<void>(
      const int socketFd, const std::string &message, std::string &response)>;
  using BaseHandlerFunction = std::function<TFuture<void>(
      const int socketFd, const std::string msgId, const std::string &message,
      std::string &response)>;
  std::unordered_map<protocol::ssmsg::SSMsgType, BaseHandlerFunction>
      ssMsgHandlerMap;
  std::unordered_map<protocol::sschatmsg::SSChatMsgType, HandlerFunction>
      ssChatHandlerMap;
  std::unique_ptr<sw::redis::Redis> redis_ptr;
  std::shared_ptr<spdlog::logger> logger;
};
