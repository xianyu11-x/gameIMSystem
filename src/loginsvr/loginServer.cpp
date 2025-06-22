#include "loginServer.h"
#include "common/BaseMsg.pb.h"
#include "coroio/promises.hpp"
#include "gatesvr/CSMsg.pb.h"
#include "spdlog/async.h"
#include "spdlog/sinks/rotating_file_sink.h"
#include "util/addressHelper.hpp"
#include "util/baseMsgHelper.h"
#include "util/config.hpp"
#include "util/uuid.hpp"
#include <iostream>
#include <memory>
#include <string>
#include <sw/redis++/redis.h>
loginServer::loginServer(NNet::TEPoll& poller, std::string address,
    int bufferSize)
    : baseServer(poller, address, bufferSize)
{
    logger = spdlog::rotating_logger_mt<spdlog::async_factory>(
        "loginSvrLogger", "logs/loginSvrLogger.txt", 1048576 * 5, 2);
    logger->set_level(spdlog::level::debug);
    logger->flush_on(spdlog::level::debug);
    auto redisAddr = configManager::getInstance().getRedisAddr();
    auto [addr, port] = parseAddress(redisAddr);
    auto ip = resolveAddress(addr);
    redis_ptr = std::make_unique<sw::redis::Redis>("tcp://" + ip + ":" + std::to_string(port));
    registerHandler();
}

void loginServer::registerHandler()
{
    // 注册处理函数
    using namespace std::placeholders;
    loginHandlerMap[protocol::ssloginmsg::SSLoginMsgType::EN_PLAYER_LOGIN] = std::bind(&loginServer::ssLogin, this, _1, _2, _3);
    loginHandlerMap[protocol::ssloginmsg::SSLoginMsgType::EN_PLAYER_LOGOUT] = std::bind(&loginServer::ssLogout, this, _1, _2, _3);
    ssMsgHandlerMap[protocol::ssmsg::SSMsgType::EN_LOGIN] = std::bind(&loginServer::loginMsgHandler, this, _1, _2, _3, _4);
}

TFuture<void> loginServer::loginMsgHandler(const int socketFd, const std::string msgId,
    const std::string& message,
    std::string& response)
{
    protocol::ssmsg::SSMsgReq req;
    req.ParseFromString(message);
    std::string ssMsgRspStr;
    co_await loginHandlerMap[req.loginreq().msgtype()](
        socketFd, req.loginreq().playerinfo().SerializeAsString(), ssMsgRspStr);
    auto [res, _] = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
        protocol::common::MsgSender::EN_MSG_SENDER_LOGINSVR,
        protocol::common::MsgBodyType::EN_RSP, ssMsgRspStr, msgId);
    response = res;
    co_return;
}

TFuture<void> loginServer::handleMessage(NNet::TEPoll::TSocket& socket,
    const std::string& message,
    std::string& response)
{
    // 处理消息并生成响应
    // std::cout << "Received message " << std::endl;
    auto msg = parseStringToBaseMsg(message);
    std::string baseMsgId = msg.msginfo().msgid();
    if (msg.msginfo().msgbodytype() == protocol::common::MsgBodyType::EN_REQ) {
        if (msg.msginfo().msgtype() == protocol::common::MsgType::EN_MSG_TYPE_SS) {
            protocol::ssmsg::SSMsgReq req;
            req.ParseFromString(msg.msgbody());
            co_await ssMsgHandlerMap[req.msgtype()](
                socket.Fd(), baseMsgId, req.SerializeAsString(), response);
        } else {
            std::cerr << "Unknown message type" << std::endl;
        }
    } else if (msg.msginfo().msgbodytype() == protocol::common::MsgBodyType::EN_RSP) {
        auto it = msgIdToCoroutineMap.find(baseMsgId);
        if (it != msgIdToCoroutineMap.end()) {
            auto coroutine = it->second;
            msgIdToResponseMap[baseMsgId] = message;
            coroutine.resume();
            msgIdToCoroutineMap.erase(it);
        } else {
            std::cerr << "No coroutine found for message ID: " << baseMsgId
                      << std::endl;
        }
    }

    co_return;
}

void loginServer::prepareSocket(NNet::TEPoll::TSocket& socket)
{
    // 在这里可以对socket进行一些预处理，比如设置非阻塞模式等
}