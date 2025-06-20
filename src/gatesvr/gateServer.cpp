#include "gateServer.h"
#include "chatsvr/SSChatMsg.pb.h"
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "coroio/corochain.hpp"
#include "coroio/promises.hpp"
#include "gatesvr/CSMsg.pb.h"
#include "loginsvr/api/sendLogoutMsg.h"
#include "spdlog/sinks/rotating_file_sink.h"
#include "util/baseMsgHelper.h"
#include "util/uuid.hpp"
#include <functional>
#include <iostream>
#include <spdlog/async.h>
#include <string>

gateServer::gateServer(NNet::TEPoll &poller, std::string address,
                       int bufferSize)
    : baseServer(poller, address, bufferSize) {
  logger = spdlog::rotating_logger_mt<spdlog::async_factory>(
      "gateSvrLogger", "logs/gateSvrLogger.txt", 1048576 * 5, 2);
  logger->set_level(spdlog::level::debug);
  logger->flush_on(spdlog::level::debug);
  registerHandler();
}

void gateServer::registerHandler() {
  // 注册处理函数
  using namespace std::placeholders;
  csLoginHandlerMap[protocol::csmsg::CSLoginMsgType::EN_PLAYER_LOGIN] =
      std::bind(&gateServer::csLogin, this, _1, _2, _3);
  csLoginHandlerMap[protocol::csmsg::CSLoginMsgType::EN_PLAYER_LOGOUT] =
      std::bind(&gateServer::csLogout, this, _1, _2, _3);
  csMsgHandlerMap[protocol::csmsg::CSMsgType::EN_LOGIN] =
      std::bind(&gateServer::loginMsgHandler, this, _1, _2, _3);
  csChatHandlerMap[protocol::csmsg::CSChatMsgType::EN_SEND] =
      std::bind(&gateServer::csSendChatMsg, this, _1, _2, _3);
  csChatHandlerMap[protocol::csmsg::CSChatMsgType::EN_HISTORY] =
      std::bind(&gateServer::csPullHistoryChatMsg, this, _1, _2, _3);
  csMsgHandlerMap[protocol::csmsg::CSMsgType::EN_CHAT] =
      std::bind(&gateServer::chatMsgHandler, this, _1, _2, _3);
  csChannelHandlerMap[protocol::csmsg::CSChannelMsgType::EN_CREATE] =
      std::bind(&gateServer::csCreateChannel, this, _1, _2, _3);
  csChannelHandlerMap[protocol::csmsg::CSChannelMsgType::EN_DESTROY] =
      std::bind(&gateServer::csDestroyChannel, this, _1, _2, _3);
  csChannelHandlerMap[protocol::csmsg::CSChannelMsgType::EN_JOIN] =
      std::bind(&gateServer::csJoinChannel, this, _1, _2, _3);
  csChannelHandlerMap[protocol::csmsg::CSChannelMsgType::EN_LEAVE] =
      std::bind(&gateServer::csLeaveChannel, this, _1, _2, _3);
  csChannelHandlerMap[protocol::csmsg::CSChannelMsgType::EN_CHANNELMSG_SEND] =
      std::bind(&gateServer::csSendChannelMsg, this, _1, _2, _3);
  csChannelHandlerMap[protocol::csmsg::CSChannelMsgType::EN_PULL] =
      std::bind(&gateServer::csPullChannelList, this, _1, _2, _3);
  csMsgHandlerMap[protocol::csmsg::CSMsgType::EN_CHANNEL] =
      std::bind(&gateServer::channelMsgHandler, this, _1, _2, _3);
  ssChatMsgHandlerMap[protocol::sschatmsg::SSChatMsgType::EN_RECEIVE] =
      std::bind(&gateServer::ssPushChatMsg, this, _1, _2, _3);
  ssMsgHandlerMap[protocol::ssmsg::SSMsgType::EN_CHAT] =
      std::bind(&gateServer::ssChatMsgHandler, this, _1, _2, _3);
  ssChannelMsgHandlerMap[protocol::sschannelmsg::SSChannelMsgType::EN_RECEIVE] =
      std::bind(&gateServer::ssPushChannelMsg, this, _1, _2, _3);
    ssMsgHandlerMap[protocol::ssmsg::SSMsgType::EN_CHANNEL] =
      std::bind(&gateServer::ssChannelMsgHandler, this, _1, _2, _3);

}

TFuture<void> gateServer::loginMsgHandler(const int socketFd,
                                          const std::string &message,
                                          std::string &response) {
  protocol::csmsg::CSMsgReq req;
  req.ParseFromString(message);
  std::string csMsgRspStr;
  co_await csLoginHandlerMap[req.loginreq().msgtype()](
      socketFd, req.loginreq().info().SerializeAsString(), csMsgRspStr);
  response = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_CS,
                           protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
                           protocol::common::MsgBodyType::EN_RSP, csMsgRspStr);
  co_return;
}

TFuture<void> gateServer::chatMsgHandler(const int socketFd,
                                         const std::string &message,
                                         std::string &response) {
  protocol::csmsg::CSMsgReq req;
  req.ParseFromString(message);
  std::string csMsgRspStr;
  co_await csChatHandlerMap[req.chatreq().msgtype()](
      socketFd, req.chatreq().SerializeAsString(), csMsgRspStr);
  response = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_CS,
                           protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
                           protocol::common::MsgBodyType::EN_RSP, csMsgRspStr);
  co_return;
}

TFuture<void> gateServer::channelMsgHandler(const int socketFd,
                                         const std::string &message,
                                         std::string &response) {
  protocol::csmsg::CSMsgReq req;
  req.ParseFromString(message);
  std::string csMsgRspStr;
  co_await csChannelHandlerMap[req.channelreq().msgtype()](
      socketFd, req.channelreq().SerializeAsString(), csMsgRspStr);
  response = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_CS,
                           protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
                           protocol::common::MsgBodyType::EN_RSP, csMsgRspStr);
  co_return;
}

TFuture<void> gateServer::ssChatMsgHandler(const int socketFd,
                                           const std::string &message,
                                           std::string &response) {
  protocol::ssmsg::SSMsgReq req;
  req.ParseFromString(message);
  std::string ssMsgRspStr;
  co_await ssChatMsgHandlerMap[req.chatreq().msgtype()](
      socketFd, req.SerializeAsString(), ssMsgRspStr);
  response = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                           protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
                           protocol::common::MsgBodyType::EN_RSP, ssMsgRspStr);
  co_return;
}

TFuture<void> gateServer::ssChannelMsgHandler(const int socketFd,
                                           const std::string &message,
                                           std::string &response) {
  protocol::ssmsg::SSMsgReq req;
  req.ParseFromString(message);
  std::string ssMsgRspStr;
  co_await ssChannelMsgHandlerMap[req.channelreq().msgtype()](
      socketFd, req.SerializeAsString(), ssMsgRspStr);
  response = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                           protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
                           protocol::common::MsgBodyType::EN_RSP, ssMsgRspStr);
  co_return;
}

TFuture<void> gateServer::handleMessage(NNet::TEPoll::TSocket &socket,
                                        const std::string &message,
                                        std::string &response) {
  // 处理消息并生成响应
  //std::cout << "Received message " << std::endl;
  logger->debug("Received a message");
  auto msg = parseStringToBaseMsg(message);
  if (msg.msginfo().msgbodytype() == protocol::common::MsgBodyType::EN_REQ) {
    if (msg.msginfo().msgtype() == protocol::common::MsgType::EN_MSG_TYPE_CS) {
      protocol::csmsg::CSMsgReq req;
      req.ParseFromString(msg.msgbody());
      co_await csMsgHandlerMap[req.csmsgtype()](
          socket.Fd(), req.SerializeAsString(), response);
    } else if (msg.msginfo().msgtype() ==
               protocol::common::MsgType::EN_MSG_TYPE_SS) {
      protocol::ssmsg::SSMsgReq req;
      req.ParseFromString(msg.msgbody());
      co_await ssMsgHandlerMap[req.msgtype()](
          socket.Fd(), req.SerializeAsString(), response);
    } else {
      std::cerr << "Unknown message type" << std::endl;
    }
  }
  // response = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_CS,
  // protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
  // protocol::common::MsgBodyType::EN_RSP, message); auto checkedMsg =
  // parserStringToBaseMsg(response); std::cout << "Parsed message: " <<
  // checkedMsg.msgbody() << std::endl; std::cout << "Parsed message type: " <<
  // checkedMsg.msginfo().msgtype() << std::endl; std::cout << "Parsed message
  // sender: " << checkedMsg.msginfo().msgsender() << std::endl; std::cout <<
  // "Parsed message body type: " << checkedMsg.msginfo().msgbodytype() <<
  // std::endl; auto& savedSocket = connectedClients.begin()->second;
  // std::string uuid = connectedClients.begin()->first;
  // std::cout<<uuid<< std::endl;
  // std::string sendStr="push to client";
  // co_await savedSocket.WriteSome(sendStr.data(), sendStr.size());
  co_return;
}

void gateServer::prepareSocket(NNet::TEPoll::TSocket &socket) {
  // 在这里可以对socket进行一些预处理，比如设置非阻塞模式等
  connectedClients.insert({socket.Fd(), &socket});
}

TFuture<void> gateServer::afterSocket(NNet::TEPoll::TSocket &socket) {
  int fd = socket.Fd();
  auto playerIdIter = socketFdToPlayerId.find(fd);
  if (playerIdIter != socketFdToPlayerId.end()) {
    auto playerId = playerIdIter->second;
    auto playerName = playerIdToPlayerName.find(playerId)->second;
    protocol::common::PlayerInfo playerInfo;
    playerInfo.set_playerid(playerId);
    playerInfo.set_playername(playerName);
    auto rsp = co_await sendLogoutMsg(
        serverPoller, playerInfo,
        protocol::common::MsgSender::EN_MSG_SENDER_GATESVR);
    protocol::ssmsg::SSMsgRsp ssMsgRsp;
    ssMsgRsp.ParseFromString(rsp);
    auto ssLogoutRsp = ssMsgRsp.loginrsp();
    if (ssLogoutRsp.issuccess()) {
      activePlayers.erase(playerName);
      playerIdToPlayerName.erase(playerId);
      std::cout << "Player logout success, player name: "
                << playerInfo.playername() << std::endl;
      logger->info("Player logout success, player name: {}",
                   playerInfo.playername());
    } else {
      std::cerr << "Player logout failed" << std::endl;
      logger->error("Player logout failed, player name: {}",
                    playerInfo.playername());
    }
  }
  socketFdToPlayerId.erase(fd);
  connectedClients.erase(fd);
  socket.Close();
  co_return;
}