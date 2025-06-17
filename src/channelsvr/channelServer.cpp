#include "channelServer.h"
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "coroio/promises.hpp"
#include "gatesvr/CSMsg.pb.h"
#include "spdlog/async.h"
#include "spdlog/sinks/rotating_file_sink.h"
#include "util/baseMsgHelper.h"
#include "util/uuid.hpp"
#include "util/config.hpp"
#include <iostream>
#include <memory>
#include <string>
#include <sw/redis++/redis.h>

channelServer::channelServer(NNet::TEPoll &poller, std::string address,
                             int bufferSize)
    : baseServer(poller, address, bufferSize) {
  logger = spdlog::rotating_logger_mt<spdlog::async_factory>(
      "channelSvrLogger", "logs/channelSvrLogger.txt", 1048576 * 5, 2);
  logger->set_level(spdlog::level::debug);
  logger->flush_on(spdlog::level::debug);
  auto redisAddr = configManager::getInstance().getRedisAddr();
  auto [addr, port] = parseAddress(redisAddr);
  auto ip = resolveAddress(addr);
  redis_ptr = std::make_unique<sw::redis::Redis>("tcp://" + ip + ":" +
                                                 std::to_string(port));
  registerHandler();
}

void channelServer::registerHandler() {
  // 注册处理函数
  using namespace std::placeholders;
  channelHandlerMap[protocol::sschannelmsg::SSChannelMsgType::EN_CREATE] =
      std::bind(&channelServer::ssCreateChannel, this, _1, _2, _3);
  channelHandlerMap[protocol::sschannelmsg::SSChannelMsgType::EN_DESTROY] =
      std::bind(&channelServer::ssDestroyChannel, this, _1, _2, _3);
  channelHandlerMap[protocol::sschannelmsg::SSChannelMsgType::EN_JOIN] =
      std::bind(&channelServer::ssJoinChannel, this, _1, _2, _3);
  channelHandlerMap[protocol::sschannelmsg::SSChannelMsgType::EN_LEAVE] =
      std::bind(&channelServer::ssLeaveChannel, this, _1, _2, _3);
  channelHandlerMap[protocol::sschannelmsg::SSChannelMsgType::EN_SEND] =
      std::bind(&channelServer::ssSendChannelMsg, this, _1, _2, _3);
  // channelHandlerMap[protocol::sschannelmsg::SSChannelMsgType::EN_HISTORY] =
  // std::bind(&channelServer::ssPullChannelHistory, this, _1, _2, _3);
  channelHandlerMap[protocol::sschannelmsg::SSChannelMsgType::EN_PULL] =
      std::bind(&channelServer::ssPullChannelList, this, _1, _2, _3);
  ssMsgHandlerMap[protocol::ssmsg::SSMsgType::EN_CHANNEL] =
      std::bind(&channelServer::channelHandler, this, _1, _2, _3);
}

TFuture<void> channelServer::channelHandler(const int socketFd,
                                            const std::string &message,
                                            std::string &response) {
  protocol::ssmsg::SSMsgReq req;
  req.ParseFromString(message);
  std::string ssMsgRspStr;
  co_await channelHandlerMap[req.channelreq().msgtype()](
      socketFd, req.SerializeAsString(), ssMsgRspStr);
  response =
      createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                    protocol::common::MsgSender::EN_MSG_SENDER_CHANNELSVR,
                    protocol::common::MsgBodyType::EN_RSP, ssMsgRspStr);
  co_return;
}

TFuture<void> channelServer::handleMessage(NNet::TEPoll::TSocket &socket,
                                           const std::string &message,
                                           std::string &response) {
  // 处理消息并生成响应
  std::cout << "Received message " << std::endl;
  auto msg = parseStringToBaseMsg(message);
  if (msg.msginfo().msgbodytype() == protocol::common::MsgBodyType::EN_REQ) {
    if (msg.msginfo().msgtype() == protocol::common::MsgType::EN_MSG_TYPE_SS) {
      protocol::ssmsg::SSMsgReq req;
      req.ParseFromString(msg.msgbody());
      co_await ssMsgHandlerMap[req.msgtype()](
          socket.Fd(), req.SerializeAsString(), response);
    } else {
      std::cerr << "Unknown message type" << std::endl;
    }
  }

  co_return;
}

void channelServer::prepareSocket(NNet::TEPoll::TSocket &socket) {
  // 在这里可以对socket进行一些预处理，比如设置非阻塞模式等
}