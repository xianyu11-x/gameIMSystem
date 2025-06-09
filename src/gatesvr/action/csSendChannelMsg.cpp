#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "coroio/corochain.hpp"
#include "gatesvr/CSMsg.pb.h"
#include "gatesvr/gateServer.h"
#include "channelsvr/api/sendChannelMsg.h"
#include <sys/socket.h>

TFuture<void> gateServer::csSendChannelMsg(const int socketFd, const std::string& message, std::string& response) {
    protocol::csmsg::CSChannelMsgReq req;
    req.ParseFromString(message);

    // 构建发送给channelsvr的消息
    protocol::ssmsg::SSMsgReq ssMsgReq;
    auto ssChannelMsgReq = ssMsgReq.mutable_channelreq();
    ssMsgReq.set_msgtype(protocol::ssmsg::SSMsgType::EN_CHANNEL);
    ssChannelMsgReq->set_msgtype(protocol::sschannelmsg::SSChannelMsgType::EN_SEND);
    ssChannelMsgReq->set_allocated_sendplayer(
        new protocol::common::PlayerInfo(req.sendplayer()));
    ssChannelMsgReq->set_allocated_channelinfo(
        new protocol::common::channelInfo(req.channelinfo()));
    
    // 复制聊天消息
    for (int i = 0; i < req.chatmessage_size(); i++) {
        ssChannelMsgReq->add_chatmessage()->CopyFrom(req.chatmessage(i));
    }

    // 发送请求到channelsvr
    auto rspStr = co_await sendChannelMsg(serverPoller, ssMsgReq, protocol::common::MsgSender::EN_MSG_SENDER_GATESVR);
    
    protocol::ssmsg::SSMsgRsp ssMsgRsp;
    ssMsgRsp.ParseFromString(rspStr);
    auto ssChannelMsgRsp = ssMsgRsp.channelrsp();

    // 构建响应给客户端的消息
    protocol::csmsg::CSMsgRsp csMsgRsp;
    csMsgRsp.set_msgtype(protocol::csmsg::CSMsgType::EN_CHANNEL);
    auto channelRsp = csMsgRsp.mutable_channelrsp();
    channelRsp->set_msgtype(protocol::csmsg::CSChannelMsgType::EN_CHANNELMSG_SEND);
    channelRsp->set_allocated_sendplayer(
        new protocol::common::PlayerInfo(ssChannelMsgRsp.sendplayer()));
    channelRsp->set_issuccess(ssChannelMsgRsp.issuccess());
    
    if (!ssChannelMsgRsp.issuccess()) {
        channelRsp->set_errmsg(ssChannelMsgRsp.errmsg());
        logger->error("Send channel message failed, player name: {}, error: {}",
                      ssChannelMsgRsp.sendplayer().playername(),
                      ssChannelMsgRsp.errmsg());
    } else {
        // 复制发送的消息到响应
        for (int i = 0; i < ssChannelMsgRsp.chatmessage_size(); i++) {
            channelRsp->add_chatmessage()->CopyFrom(ssChannelMsgRsp.chatmessage(i));
        }
        logger->info("Send channel message success, player name: {}, channel name: {}, message count: {}",
                     ssChannelMsgRsp.sendplayer().playername(),
                     req.channelinfo().channelname(),
                     ssChannelMsgReq->chatmessage_size());
    }
    
    response = csMsgRsp.SerializeAsString();
    co_return;
}
