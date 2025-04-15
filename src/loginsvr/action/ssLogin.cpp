#include "common/SSMsg.pb.h"
#include "common/player.pb.h"
#include "loginsvr/loginServer.h"
#include "util/uuid.hpp"
#include <iostream>

TFuture<void> loginServer::ssLogin(const int socketFd,
                                   const std::string &message,
                                   std::string &response) {
  protocol::common::PlayerInfo playerInfo;
  if (!playerInfo.ParseFromString(message)) {
    std::cerr << "Failed to parse login player" << std::endl;
    co_return;
  }
  auto curPlayerName = playerInfo.playername();
  bool isNewUser = false;
  // 检查是否是新用户写数据库

  //
  protocol::ssmsg::SSMsgRsp rsp;
  rsp.set_msgtype(protocol::ssmsg::SSMsgType::EN_LOGIN);
  auto loginRsp = rsp.mutable_loginrsp();
  loginRsp->set_msgtype(protocol::ssloginmsg::SSLoginMsgType::EN_PLAYER_LOGIN);
  auto loginedPlayer = loginRsp->mutable_playerinfo();
  loginedPlayer->set_playerid(nextPlayerId++);
  loginedPlayer->set_playertoken(generateUUID());
  loginedPlayer->set_playername(curPlayerName);
  loginRsp->set_issuccess(true);
  response = rsp.SerializeAsString();
  std::cout << "player name: " << curPlayerName << std::endl;
  co_return;
}