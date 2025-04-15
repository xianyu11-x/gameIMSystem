#include "common/SSMsg.pb.h"
#include "common/player.pb.h"
#include "loginsvr/loginServer.h"
#include "util/uuid.hpp"
#include <iostream>

TFuture<void> loginServer::ssLogout(const int socketFd,const std::string& message, std::string& response){
    protocol::common::PlayerInfo playerInfo;
    if (!playerInfo.ParseFromString(message)) {
        std::cerr << "Failed to parse player info" << std::endl;
        co_return;
    }



    protocol::ssmsg::SSMsgRsp rsp;
    rsp.set_msgtype(protocol::ssmsg::SSMsgType::EN_LOGIN);
    auto loginRsp = rsp.mutable_loginrsp();
    loginRsp->set_msgtype(protocol::ssloginmsg::SSLoginMsgType::EN_PLAYER_LOGOUT);
    auto loginedPlayer = loginRsp->mutable_playerinfo();
    loginRsp->set_issuccess(true);
    response = rsp.SerializeAsString();
    std::cout << "logout player name: " << playerInfo.playername() << std::endl;
    co_return;
}