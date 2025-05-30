#include "chatsvr/chatServer.h"
#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "coroio/corochain.hpp"
#include "util/uuid.hpp"
#include <iterator>
#include <sw/redis++/command_options.h>
#include <vector>

TFuture<void> chatServer::ssPullHistoryChatMsg(const int socketFd,
                                               const std::string &message,
                                               std::string &response) {
  protocol::ssmsg::SSMsgReq req;
  req.ParseFromString(message);
  auto ssChatMsgReq = req.chatreq();
  auto sendPlayerName = ssChatMsgReq.sendplayer().playername();
  auto sendPlayerId = redis_ptr->get("username:" + sendPlayerName);

  std::unordered_map<std::string, std::string> unreadMsgSeq;
  redis_ptr->hgetall("chat:unread:" + *sendPlayerId,
                     std::inserter(unreadMsgSeq, unreadMsgSeq.begin()));

  protocol::ssmsg::SSMsgRsp rsp;
  rsp.set_msgtype(req.msgtype());
  auto chatRsp = rsp.mutable_chatrsp();
  chatRsp->set_msgtype(ssChatMsgReq.msgtype());
  chatRsp->set_allocated_sendplayer(
      new protocol::common::PlayerInfo(ssChatMsgReq.sendplayer()));

  for (auto &[msgSendPlayerId, msgSeq] : unreadMsgSeq) {
    auto lastAckStr =
        redis_ptr->get("chat:ack:" + msgSendPlayerId + ":" + *sendPlayerId);
    int lastAck = 0;
    if (lastAckStr) {
      lastAck = std::stoi(lastAckStr.value());
    }
    std::vector<std::string> chatMsgList;
    int msgSeqInt = std::stoi(msgSeq) + 1;
    redis_ptr->zrangebyscore(
        "chat:message:" + msgSendPlayerId + ":" + *sendPlayerId,
        sw::redis::BoundedInterval<double>(lastAck, msgSeqInt,
                                           sw::redis::BoundType::OPEN),
        std::back_inserter(chatMsgList));
    for (auto &chatMsg : chatMsgList) {
      protocol::common::chatMessage chatMessage;
      chatMessage.ParseFromString(chatMsg);
      chatRsp->add_chatmessage()->CopyFrom(chatMessage);
    }
    redis_ptr->set("chat:ack:" + msgSendPlayerId + ":" + *sendPlayerId, msgSeq);
    redis_ptr->hdel("chat:unread:" + *sendPlayerId, msgSendPlayerId);
  }
  
  chatRsp->set_issuccess(true);
  logger->info("Pull history chat message success, player name: {}",
               ssChatMsgReq.sendplayer().playername());
  response = rsp.SerializeAsString();
  co_return;
}