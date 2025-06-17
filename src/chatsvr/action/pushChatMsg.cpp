#include "chatsvr/SSChatMsg.pb.h"
#include "chatsvr/chatServer.h"
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "coroio/all.hpp"
#include "coroio/epoll.hpp"
#include "coroio/promises.hpp"
#include "util/baseMsgHelper.h"
#include "util/config.hpp"
#include "util/sendMsg.h"
NNet::TVoidTask
chatServer::ssPushMsg(const protocol::sschatmsg::SSChatMsgReq ssChatMsg,
                      protocol::common::MsgSender msgSender, int expectAck) {
  protocol::ssmsg::SSMsgReq req;
  req.set_msgtype(protocol::ssmsg::SSMsgType::EN_CHAT);
  auto chatReq = req.mutable_chatreq();
  chatReq->set_msgtype(protocol::sschatmsg::SSChatMsgType::EN_RECEIVE);
  chatReq->set_allocated_sendplayer(
      new protocol::common::PlayerInfo(ssChatMsg.sendplayer()));
  chatReq->set_allocated_receiveplayer(
      new protocol::common::PlayerInfo(ssChatMsg.receiveplayer()));

  // TODO::从数据库中获取可能更好一些
  for (int i = 0; i < ssChatMsg.chatmessage_size(); i++) {
    chatReq->add_chatmessage()->CopyFrom(ssChatMsg.chatmessage(i));
  }
  auto baseMsg = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_SS,
                               msgSender, protocol::common::MsgBodyType::EN_REQ,
                               req.SerializeAsString());
  std::string address = configManager::getInstance().getGateServerAddr();
  auto baseMsgRspStr = co_await sendMsg(serverPoller, address, baseMsg);
  auto baseMsgRsp = parseStringToBaseMsg(baseMsgRspStr);
  auto ssMsgRsp = baseMsgRsp.msgbody();
  protocol::ssmsg::SSMsgRsp rsp;
  rsp.ParseFromString(ssMsgRsp);
  auto chatRsp = rsp.chatrsp();
  if (chatRsp.issuccess()) {
    std::cout << "Push message success" << std::endl;
    auto sendPlayerName = ssChatMsg.sendplayer().playername();
    auto receivePlayerName = ssChatMsg.receiveplayer().playername();
    auto sendPlayerId = redis_ptr->get("username:" + sendPlayerName);
    auto receivePlayerId = redis_ptr->get("username:" + receivePlayerName);
    auto curAck = redis_ptr->get(
        "chat:ack:" + *sendPlayerId + ":" +
        *receivePlayerId);
    int curAckVal = 0;
    if (curAck) {
      curAckVal = std::stoi(curAck.value());
    }
    if (!curAck || expectAck > curAckVal) {
      redis_ptr->set(
          "chat:ack:" + *sendPlayerId +
              ":" + *receivePlayerId,
          std::to_string(expectAck));
    }
    logger->info("Push message success, send player: {}, receive player: {},msg ack: {}",
                 sendPlayerName, receivePlayerName,expectAck);
  } else {
    std::cerr << "Push message failed: " << chatRsp.errmsg() << std::endl;
    logger->error("Push message failed: {}", chatRsp.errmsg());
  }
}
