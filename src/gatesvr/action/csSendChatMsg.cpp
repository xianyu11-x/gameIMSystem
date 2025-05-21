#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "coroio/corochain.hpp"
#include "gatesvr/CSMsg.pb.h"
#include "gatesvr/gateServer.h"
#include "chatsvr/sdk/sendChatMsg.h"
#include <sys/socket.h>

TFuture<void> gateServer::csSendChatMsg(const int socketFd,const std::string& message, std::string& response){
    protocol::csmsg::CSChatMsgReq req;
    req.ParseFromString(message);

    protocol::ssmsg::SSMsgReq ssMsgReq;
    auto ssChatMsgReq = ssMsgReq.mutable_chatreq();
    ssMsgReq.set_msgtype(protocol::ssmsg::SSMsgType::EN_CHAT);
    ssChatMsgReq->set_msgtype(protocol::sschatmsg::SSChatMsgType::EN_SEND);
    ssChatMsgReq->set_allocated_sendplayer(
        new protocol::common::PlayerInfo(req.sendplayer()));
    ssChatMsgReq->set_allocated_receiveplayer(
        new protocol::common::PlayerInfo(req.receiveplayer()));
    for(int i = 0;i<req.chatmessage_size();i++){
        ssChatMsgReq->add_chatmessage()->CopyFrom(req.chatmessage(i));    
    }
    auto rspStr = co_await sendChatMsg(serverPoller, ssMsgReq, protocol::common::MsgSender::EN_MSG_SENDER_GATESVR);
    
    protocol::ssmsg::SSMsgRsp ssMsgRsp;
    ssMsgRsp.ParseFromString(rspStr);
    auto ssChatMsgRsp = ssMsgRsp.chatrsp();

    protocol::csmsg::CSMsgRsp csMsgRsp;
    csMsgRsp.set_msgtype(protocol::csmsg::CSMsgType::EN_CHAT);
    auto chatRsp = csMsgRsp.mutable_chatrsp();
    chatRsp->set_msgtype(protocol::csmsg::CSChatMsgType::EN_SEND);
    chatRsp->set_allocated_sendplayer(
        new protocol::common::PlayerInfo(ssChatMsgRsp.sendplayer()));
    chatRsp->set_issuccess(ssChatMsgRsp.issuccess());
    if(!ssChatMsgRsp.issuccess()){
        chatRsp->set_errmsg(ssChatMsgRsp.errmsg());
        logger->error("Send chat message failed, player name: {},error: {}",
                      ssChatMsgRsp.sendplayer().playername(),
                      ssChatMsgRsp.errmsg());
    }else{
        logger->info("Send chat message success, player name: {}",
                     ssChatMsgRsp.sendplayer().playername());
    }
    response = csMsgRsp.SerializeAsString();
    co_return;
}