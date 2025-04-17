#include "common/SSMsg.pb.h"
#include "common/player.pb.h"
#include "loginsvr/loginServer.h"
#include "util/uuid.hpp"
#include <iostream>

TFuture<void> loginServer::ssLogout(const int socketFd,const std::string& message, std::string& response){
    protocol::common::PlayerInfo playerInfo;
    if (!playerInfo.ParseFromString(message)) {
        std::cerr << "Failed to parse player info" << std::endl;
        logger->error("Failed to parse player info");
        co_return;
    }

    protocol::ssmsg::SSMsgRsp rsp;
    rsp.set_msgtype(protocol::ssmsg::SSMsgType::EN_LOGIN);
    auto loginRsp = rsp.mutable_loginrsp();
    loginRsp->set_msgtype(protocol::ssloginmsg::SSLoginMsgType::EN_PLAYER_LOGOUT);
    auto loginedPlayer = loginRsp->mutable_playerinfo();
    auto savedPlayerInfo = redis_ptr->get("user:" + std::to_string(playerInfo.playerid()));
    if(savedPlayerInfo){
        if(redis_ptr->srem("onlineSet", std::to_string(playerInfo.playerid()))){
            std::cout << "logout player name: " << playerInfo.playername() << std::endl;
            logger->info("logout player name: {}", playerInfo.playername());
            loginedPlayer->set_playerid(playerInfo.playerid());
            loginedPlayer->set_playername(playerInfo.playername());
            loginedPlayer->set_playertoken(playerInfo.playertoken());
            loginRsp->set_issuccess(true);
            response = rsp.SerializeAsString();
            co_return;
        }else{
            logger->error("logout player is not online, player name: {}", playerInfo.playername());
        }
    }else{
        logger->error("not available player info");
    }
    loginRsp->set_issuccess(false);
    response = rsp.SerializeAsString();
    co_return;
}