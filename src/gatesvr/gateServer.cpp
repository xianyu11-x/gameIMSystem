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
}

TVoidTask gateServer::handleMessage(NNet::TEPoll::TSocket &socket,
                                    const std::string &message,
                                    std::string &response) {
  // 处理消息并生成响应
  std::cout << "Received message " << std::endl;
  auto msg = parseStringToBaseMsg(message);
  if (msg.msginfo().msgbodytype() == protocol::common::MsgBodyType::EN_REQ) {
    if (msg.msginfo().msgtype() == protocol::common::MsgType::EN_MSG_TYPE_CS) {
      protocol::csmsg::CSMsgReq req;
      req.ParseFromString(msg.msgbody());
      if (req.csmsgtype() == protocol::csmsg::CSMsgType::EN_LOGIN) {
        loginHandlerMap[req.loginreq().msgtype()](
            socket.Fd(), req.loginreq().info().SerializeAsString(), response);
      }
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