#include "gatesvr/gateServer.h"
#include "util/sendMsg.h"
#include <sys/socket.h>

TVoidTask gateServer::csLogin(const int socketFd,const std::string& message, std::string& response){
    protocol::common::PlayerInfo playerInfo;
        if (!playerInfo.ParseFromString(message)) {
            std::cerr << "Failed to parse login player" << std::endl;
            co_return;
        }


        auto curPlayerName = playerInfo.playername();
        if(activePlayers.find(curPlayerName) != activePlayers.end()) {
            std::cerr << "Player already logged in" << std::endl;
            //co_await activePlayers[curPlayerName]->WriteSome("Player already logged in", 24);
            co_return;
        }

        //TODO:向实际loginsvr发送登录请求
        auto rsp = co_await sendMsg(serverPoller, "127.0.0.1:10001", "123455");


        protocol::csmsg::CSMsgRsp msgRsp;
        msgRsp.set_msgtype(protocol::csmsg::CSMsgType::EN_CHAT);
        auto loginRsp = msgRsp.mutable_loginrsp();
        loginRsp->set_msgtype(protocol::csmsg::CSLoginMsgType::EN_PLAYER_LOGIN);
        auto loginedPlayer = loginRsp->mutable_info();
        //目前简单返回一下
        loginedPlayer->set_playertoken("213456789");
        loginedPlayer->set_playername(playerInfo.playername());
        loginedPlayer->set_playerid(123456);
        loginRsp->set_issuccess(true);
        response = msgRsp.SerializeAsString();
        auto it = connectedClients.find(socketFd);
        if(it != connectedClients.end()){
            activePlayers.insert({playerInfo.playername(), it->second});
        }
        
        co_return;
}