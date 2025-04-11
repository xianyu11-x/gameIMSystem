#include "loginServer.h"
#include "common/BaseMsg.pb.h"
#include "coroio/promises.hpp"
#include "gatesvr/CSMsg.pb.h"
#include "util/baseMsgHelper.h"
#include "util/uuid.hpp"
#include <iostream>
#include <string>

loginServer::loginServer(NNet::TEPoll& poller,std::string address,int bufferSize):baseServer(poller,address,bufferSize) { registerHandler(); }

void loginServer::registerHandler() {
  // 注册处理函数
  using namespace std::placeholders;

}

TVoidTask loginServer::handleMessage(NNet::TEPoll::TSocket &socket,
                                    const std::string &message,
                                    std::string &response) {
  // 处理消息并生成响应
  std::cout << "Received message " << std::endl;
  response = "login success";
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

void loginServer::prepareSocket(NNet::TEPoll::TSocket &socket) {
  // 在这里可以对socket进行一些预处理，比如设置非阻塞模式等
}