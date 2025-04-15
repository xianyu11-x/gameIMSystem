#include "gateServer.h"
#include "common/BaseMsg.pb.h"
#include "coroio/promises.hpp"
#include "gatesvr/CSMsg.pb.h"
#include "util/baseMsgHelper.h"
#include "util/uuid.hpp"
#include <iostream>
#include <string>

gateServer::gateServer(NNet::TEPoll& poller,std::string address,int bufferSize):baseServer(poller,address,bufferSize) { registerHandler(); }

void gateServer::registerHandler() {
  // 注册处理函数
  using namespace std::placeholders;
  loginHandlerMap[protocol::csmsg::CSLoginMsgType::EN_PLAYER_LOGIN] =
      std::bind(&gateServer::csLogin, this, _1, _2, _3);
  loginHandlerMap[protocol::csmsg::CSLoginMsgType::EN_PLAYER_LOGOUT] =
      std::bind(&gateServer::csLogout, this, _1, _2, _3);
  csMsgHandlerMap[protocol::csmsg::CSMsgType::EN_LOGIN] =
      std::bind(&gateServer::loginMsgHandler, this, _1, _2, _3);
}


TFuture<void> gateServer::loginMsgHandler(const int socketFd,const std::string& message, std::string& response){
  protocol::csmsg::CSMsgReq req;
  req.ParseFromString(message);
  std::string csMsgRspStr;
  co_await loginHandlerMap[req.loginreq().msgtype()](socketFd, req.loginreq().info().SerializeAsString(), csMsgRspStr);
  response = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_CS,
                                    protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
                                    protocol::common::MsgBodyType::EN_RSP, csMsgRspStr);
  co_return;
}

TFuture<void> gateServer::handleMessage(NNet::TEPoll::TSocket &socket,
                                    const std::string &message,
                                    std::string &response) {
  // 处理消息并生成响应
  std::cout << "Received message " << std::endl;
  auto msg = parseStringToBaseMsg(message);
  if (msg.msginfo().msgbodytype() == protocol::common::MsgBodyType::EN_REQ) {
    if (msg.msginfo().msgtype() == protocol::common::MsgType::EN_MSG_TYPE_CS) {
      protocol::csmsg::CSMsgReq req;
      req.ParseFromString(msg.msgbody());
      co_await csMsgHandlerMap[req.csmsgtype()](socket.Fd(), req.SerializeAsString(), response);
    }else if(msg.msginfo().msgtype() == protocol::common::MsgType::EN_MSG_TYPE_SS){

    }else{
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