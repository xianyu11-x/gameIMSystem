#include "common/SSMsg.pb.h"
#include "gatesvr/CSMsg.pb.h"
#include "gatesvr/gateServer.h"
#include "util/baseMsgHelper.h"
#include "util/sendMsg.h"
TFuture<void> gateServer::ssPushChatMsg(const int socketFd,const std::string& message, std::string& response){
    protocol::ssmsg::SSMsgReq req;
    req.ParseFromString(message);
    auto ssChatMsg = req.chatreq();

    protocol::ssmsg::SSMsgRsp rsp;
    rsp.set_msgtype(req.msgtype());
    auto ssChatRsp = rsp.mutable_chatrsp();
    ssChatRsp->set_msgtype(ssChatMsg.msgtype());
    ssChatRsp->set_allocated_sendplayer(new protocol::common::PlayerInfo(ssChatMsg.sendplayer()));
    

    protocol::csmsg::CSMsgReq csMsgReq;
    csMsgReq.set_csmsgtype(protocol::csmsg::CSMsgType::EN_CHAT);
    auto chatReq = csMsgReq.mutable_chatreq();
    chatReq->set_msgtype(protocol::csmsg::CSChatMsgType::EN_RECEIVE);
    chatReq->set_allocated_sendplayer(new protocol::common::PlayerInfo(ssChatMsg.sendplayer()));
    chatReq->set_allocated_receiveplayer(new protocol::common::PlayerInfo(ssChatMsg.receiveplayer()));
    for(int i = 0;i<ssChatMsg.chatmessage_size();i++){
        chatReq->add_chatmessage()->CopyFrom(ssChatMsg.chatmessage(i));
    }
    auto baseMsg = createBaseMsg(protocol::common::MsgType::EN_MSG_TYPE_CS,
                                 protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
                                 protocol::common::MsgBodyType::EN_REQ, csMsgReq.SerializeAsString());
    auto it = activePlayers.find(ssChatMsg.receiveplayer().playername());
    if(it != activePlayers.end()){
        auto csBaseRsp = co_await sendMsg(it->second, baseMsg);
        wakeUpClientCoroutine(it->second);
        auto baseMsgRsp = parseStringToBaseMsg(csBaseRsp);
        auto csMsgRsp = baseMsgRsp.msgbody();
        protocol::csmsg::CSMsgRsp csRsp;
        csRsp.ParseFromString(csMsgRsp);
        auto csChatRsp = csRsp.chatrsp();
        if(csChatRsp.issuccess()){
            std::cout << "Push message success" << std::endl;
            logger->info("Push message success");
            ssChatRsp->set_issuccess(true);
        }else{
            std::cerr << "Push message failed: " << csChatRsp.errmsg() << std::endl;
            logger->error("Push message failed: {}", csChatRsp.errmsg());
            ssChatRsp->set_issuccess(false);
            ssChatRsp->set_errmsg(csChatRsp.errmsg());
        }
    }else{
        std::cerr << "Player not online" << std::endl;
        logger->error("Player not online");
        ssChatRsp->set_issuccess(false);
        ssChatRsp->set_errmsg("Player not online");
    }

    response = rsp.SerializeAsString();
    co_return;
}