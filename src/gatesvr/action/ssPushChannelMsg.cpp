#include "common/SSMsg.pb.h"
#include "coroio/corochain.hpp"
#include "gatesvr/CSMsg.pb.h"
#include "gatesvr/gateServer.h"
#include "util/baseMsgHelper.h"
#include <cstddef>

TFuture<ssize_t>
gateServer::sendChannelMsgToClient(const std::string message,
    const std::string playerName,
    const int playerId)
{
    auto playerSocket = activePlayers.find(playerName)->second;
    logger->debug("playerFd {},from {}", playerSocket->Fd(), playerName);
    auto [baseMsg, msgId] = createBaseMsg(
        protocol::common::MsgType::EN_MSG_TYPE_CS,
        protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
        protocol::common::MsgBodyType::EN_REQ, message);
    auto baseMsgRsp = co_await pendSendMsg(playerSocket->Fd(), baseMsg, msgId);
    // localLogger->debug("receive rsp,from {}", memberName);
    auto baseMsgRspParsed = parseStringToBaseMsg(baseMsgRsp);
    auto csMsgRsp = baseMsgRspParsed.msgbody();
    protocol::csmsg::CSMsgRsp csRsp;
    csRsp.ParseFromString(csMsgRsp);
    if (!csRsp.channelrsp().issuccess()) {
        logger->error("Push channel message to player {} failed: {}", playerName,
            csRsp.channelrsp().errmsg());
        co_return -1;
    }
    co_return 0;
}

TFuture<void> gateServer::ssPushChannelMsg(const int socketFd,
    const std::string& message,
    std::string& response)
{
    protocol::ssmsg::SSMsgReq req;
    req.ParseFromString(message);
    auto ssChannelMsg = req.channelreq();

    protocol::ssmsg::SSMsgRsp rsp;
    rsp.set_msgtype(req.msgtype());
    auto ssChannelRsp = rsp.mutable_channelrsp();
    ssChannelRsp->set_msgtype(ssChannelMsg.msgtype());
    ssChannelRsp->set_allocated_sendplayer(
        new protocol::common::PlayerInfo(ssChannelMsg.sendplayer()));

    // 构建推送给客户端的消息
    protocol::csmsg::CSMsgReq csMsgReq;
    csMsgReq.set_csmsgtype(protocol::csmsg::CSMsgType::EN_CHANNEL);
    auto channelReq = csMsgReq.mutable_channelreq();
    channelReq->set_msgtype(
        protocol::csmsg::CSChannelMsgType::EN_CHANNELMSG_RECEIVE);
    channelReq->set_allocated_sendplayer(
        new protocol::common::PlayerInfo(ssChannelMsg.sendplayer()));
    channelReq->set_allocated_channelinfo(
        new protocol::common::channelInfo(ssChannelMsg.channelinfo()));

    // 复制聊天消息
    for (int i = 0; i < ssChannelMsg.chatmessage_size(); i++) {
        channelReq->add_chatmessage()->CopyFrom(ssChannelMsg.chatmessage(i));
    }

    // auto [baseMsg,msgId] = createBaseMsg(
    //     protocol::common::MsgType::EN_MSG_TYPE_CS,
    //     protocol::common::MsgSender::EN_MSG_SENDER_GATESVR,
    //     protocol::common::MsgBodyType::EN_REQ, csMsgReq.SerializeAsString());
    std::string csMsgReqStr = csMsgReq.SerializeAsString();
    // 查找目标频道的所有在线成员并推送消息
    bool pushSuccess = true;
    std::string pushError = "";
    std::vector<TFuture<ssize_t>> futures;

    // 获取频道成员列表
    if (ssChannelMsg.channelinfo().members_size() > 0) {
        // auto& localActivePlayers = activePlayers;
        // auto localLogger = logger;
        // auto localWakeUpFunction= [this](NNet::TEPoll::TSocket *socket) {
        //   wakeUpClientCoroutine(socket);
        // };
        for (int i = 0; i < ssChannelMsg.channelinfo().members_size(); i++) {
            auto member = ssChannelMsg.channelinfo().members(i);
            auto memberid = member.playerid();
            auto memberName = playerIdToPlayerName.find(memberid)->second;
            auto it = activePlayers.find(memberName);
            if (it != activePlayers.end()) {
                futures.push_back(sendChannelMsgToClient(csMsgReqStr, memberName, memberid));
            }
        }
    }
    auto pushResults = co_await All(std::move(futures));
    for (const auto& result : pushResults) {
        if (result < 0) {
            pushSuccess = false;
            pushError = "Failed to push message to all channel members";
            break;
        }
    }

    if (pushSuccess) {
        ssChannelRsp->set_issuccess(true);
        logger->info("Push channel message success, channel: {}, sender: {}",
            ssChannelMsg.channelinfo().channelname(),
            ssChannelMsg.sendplayer().playername());
    } else {
        ssChannelRsp->set_issuccess(false);
        ssChannelRsp->set_errmsg(pushError);
        logger->error("Push channel message failed: {}, channel: {}, sender: {}",
            pushError, ssChannelMsg.channelinfo().channelname(),
            ssChannelMsg.sendplayer().playername());
    }

    response = rsp.SerializeAsString();
    co_return;
}
