#include "chatServer.h"
#include "chatsvr/SSChatMsg.pb.h"
#include "coroio/corochain.hpp"
#include "spdlog/async.h"
#include "spdlog/sinks/rotating_file_sink.h"
#include "util/baseMsgHelper.h"
#include "util/config.hpp"
chatServer::chatServer(NNet::TEPoll &poller, std::string address,
                       int bufferSize)
    : baseServer(poller, address, bufferSize) {
  logger = spdlog::rotating_logger_mt<spdlog::async_factory>(
      "chatSvrLogger", "logs/chatSvrLogger.txt", 1048576 * 5, 2);
  logger->set_level(spdlog::level::debug);
  logger->flush_on(spdlog::level::debug);
  auto redisAddr = configManager::getInstance().getRedisAddr();
  auto [addr, port] = parseAddress(redisAddr);
  auto ip = resolveAddress(addr);
  redis_ptr = std::make_unique<sw::redis::Redis>("tcp://" + ip + ":" +
                                                 std::to_string(port));
  registerHandler();
}

void chatServer::registerHandler() {
  // 注册处理函数
  using namespace std::placeholders;
  ssChatHandlerMap[protocol::sschatmsg::SSChatMsgType::EN_HISTORY] =
      std::bind(&chatServer::ssPullHistoryChatMsg, this, _1, _2, _3);
  ssChatHandlerMap[protocol::sschatmsg::SSChatMsgType::EN_SEND] =
      std::bind(&chatServer::ssSendChatMsg, this, _1, _2, _3);
  ssMsgHandlerMap[protocol::ssmsg::SSMsgType::EN_CHAT] =
      std::bind(&chatServer::chatMsgHandler, this, _1, _2, _3,_4);
}

TFuture<void> chatServer::chatMsgHandler(const int socketFd, const std::string msgId,
                                         const std::string &message,
                                         std::string &response) {
  protocol::ssmsg::SSMsgReq req;
  req.ParseFromString(message);
  std::string ssMsgRspStr;
  co_await ssChatHandlerMap[req.chatreq().msgtype()](
      socketFd, req.SerializeAsString(), ssMsgRspStr);
  auto [res, _] =
      createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                    protocol::common::MsgSender::EN_MSG_SENDER_CHATSVR,
                    protocol::common::MsgBodyType::EN_RSP, ssMsgRspStr,msgId);
  response = res;
}

TFuture<void> chatServer::handleMessage(NNet::TEPoll::TSocket &socket,
                                        const std::string &message,
                                        std::string &response) {
  // 处理消息并生成响应
  // std::cout << "Received message " << std::endl;
  auto msg = parseStringToBaseMsg(message);
  std::string baseMsgId = msg.msginfo().msgid();
  if (msg.msginfo().msgbodytype() == protocol::common::MsgBodyType::EN_REQ) {
    if (msg.msginfo().msgtype() == protocol::common::MsgType::EN_MSG_TYPE_SS) {
      protocol::ssmsg::SSMsgReq req;
      req.ParseFromString(msg.msgbody());
      if (ssMsgHandlerMap.find(req.msgtype()) == ssMsgHandlerMap.end()) {
        std::cerr << "Unknown message type" << std::endl;
        co_return;
      }
      co_await ssMsgHandlerMap[req.msgtype()](
          socket.Fd(), baseMsgId,req.SerializeAsString(), response);
    } else {
      std::cerr << "Unknown message type" << std::endl;
    }
  }

  co_return;
}