#include "common/SSMsg.pb.h"
#include "common/player.pb.h"
#include "loginsvr/loginServer.h"
#include "util/uuid.hpp"
#include <cstdint>
#include <iostream>

TFuture<void> loginServer::ssLogin(const int socketFd,
                                   const std::string &message,
                                   std::string &response) {
  protocol::common::PlayerInfo playerInfo;
  if (!playerInfo.ParseFromString(message)) {
    std::cerr << "Failed to parse login player" << std::endl;
    logger->error("Failed to parse login player");
    co_return;
  }
  auto curPlayerName = playerInfo.playername();
  // 检查是否是新用户写数据库
  auto userIdStr = redis_ptr->get("username:" + curPlayerName);
  if (!userIdStr) {
    int64_t userId = redis_ptr->incr("global:userid:count");
    playerInfo.set_playerid(userId);
    redis_ptr->set("username:" + curPlayerName, std::to_string(userId));
    redis_ptr->set("user:" + std::to_string(userId),
                   playerInfo.SerializeAsString());
  } else {
    playerInfo.set_playerid(std::stoll(userIdStr.value()));
  }

  protocol::ssmsg::SSMsgRsp rsp;
  rsp.set_msgtype(protocol::ssmsg::SSMsgType::EN_LOGIN);
  auto loginRsp = rsp.mutable_loginrsp();
  loginRsp->set_msgtype(protocol::ssloginmsg::SSLoginMsgType::EN_PLAYER_LOGIN);
  auto loginedPlayer = loginRsp->mutable_playerinfo();
  loginedPlayer->set_playerid(playerInfo.playerid());

  loginedPlayer->set_playername(curPlayerName);
  if(redis_ptr->sismember("onlineSet", std::to_string(playerInfo.playerid()))) {
    std::cerr << "Player already logged in" << std::endl;
    logger->warn("Player already logged in, player name: {}",
                 playerInfo.playername());
    loginRsp->set_issuccess(false);
    response = rsp.SerializeAsString();
    co_return;
  }
  loginRsp->set_issuccess(true);
  loginedPlayer->set_playertoken(generateUUID());
  redis_ptr->sadd("onlineSet", std::to_string(playerInfo.playerid()));

  response = rsp.SerializeAsString();

  std::cout << "player name: " << curPlayerName << std::endl;
  logger->info("player name: {}", curPlayerName);
  co_return;
}