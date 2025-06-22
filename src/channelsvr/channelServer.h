#include "channelsvr/SSChannelMsg.pb.h"
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "common/chatMessage.pb.h"
#include "common/player.pb.h"
#include "coroio/all.hpp"
#include "coroio/corochain.hpp"
#include "coroio/epoll.hpp"
#include "coroio/promises.hpp"
#include "spdlog/logger.h"
#include "util/server.h"
#include <functional>
#include <string>
#include <sw/redis++/redis++.h>
#include <unordered_map>
#include <vector>
#pragma once

class channelServer : public baseServer {
public:
  channelServer(NNet::TUring &poller, std::string address, int bufferSize);
  ~channelServer() override = default;

private:
  TFuture<void> ssPullChannelList(const int socketFd,
                                  const std::string &message,
                                  std::string &response);
  TFuture<void> ssPullChannelHistory(const int socketFd,
                                     const std::string &message,
                                     std::string &response);
  TFuture<void> ssSendChannelMsg(const int socketFd, const std::string &message,
                                 std::string &response);
  TFuture<void> ssLeaveChannel(const int socketFd, const std::string &message,
                               std::string &response);
  TFuture<void> ssJoinChannel(const int socketFd, const std::string &message,
                              std::string &response);
  TFuture<void> ssCreateChannel(const int socketFd, const std::string &message,
                                std::string &response);
  TFuture<void> ssDestroyChannel(const int socketFd, const std::string &message,
                                 std::string &response);
  TFuture<void> channelHandler(const int socketFd, const std::string msgId,const std::string &message,
                               std::string &response);
  TVoidTask ssPushChannelMsg(
      std::unordered_set<std::string> members,
      protocol::common::channelInfo channelInfo,
      protocol::common::PlayerInfo sendPlayer,
      std::vector<protocol::common::chatMessage> channelChatMessageList,
      protocol::common::MsgSender msgSender);
  void registerHandler();
  TFuture<void> handleMessage(NNet::TUring::TSocket &socket,
                              const std::string &message,
                              std::string &response) override;
  void prepareSocket(NNet::TUring::TSocket &socket) override;
  TFuture<void> afterSocket(NNet::TUring::TSocket &socket) override {
    co_return;
  };

  using HandlerFunction = std::function<TFuture<void>(
      const int socketFd, const std::string &message, std::string &response)>;
  using BaseHandlerFunction = std::function<TFuture<void>(
      const int socketFd, const std::string msgId, const std::string &message,
      std::string &response)>;
  std::unordered_map<protocol::sschannelmsg::SSChannelMsgType, HandlerFunction>
      channelHandlerMap;
  std::unordered_map<protocol::ssmsg::SSMsgType, BaseHandlerFunction>
      ssMsgHandlerMap;

  std::unique_ptr<sw::redis::Redis> redis_ptr;
  std::shared_ptr<spdlog::logger> logger;
};