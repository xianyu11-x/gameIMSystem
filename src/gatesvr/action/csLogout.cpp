#include "common/SSMsg.pb.h"
#include "gatesvr/gateServer.h"
#include "loginsvr/sdk/sendLogoutMsg.h"

TFuture<void> gateServer::csLogout(const int socketFd,
                                   const std::string &message,
                                   std::string &response) {
  protocol::common::PlayerInfo playerInfo;
  if (!playerInfo.ParseFromString(message)) {
    std::cerr << "Failed to parse player info" << std::endl;
    logger->error("Failed to parse player info");
    co_return;
  }
  std::string curPlayerName = playerInfo.playername();
  if (activePlayers.find(curPlayerName) == activePlayers.end()) {
    std::cerr << "Player already logged out" << std::endl;
    logger->warn("Player already logged out, player name: {}",
                 playerInfo.playername());
    co_return;
  }
  auto res = co_await sendLogoutMsg(
      serverPoller, playerInfo,
      protocol::common::MsgSender::EN_MSG_SENDER_GATESVR);
  protocol::ssmsg::SSMsgRsp rsp;
  rsp.ParseFromString(res);
  auto ssLogoutRsp = rsp.loginrsp();
  protocol::csmsg::CSMsgRsp csRsp;
  csRsp.set_msgtype(protocol::csmsg::CSMsgType::EN_LOGIN);
  auto logoutRsp = csRsp.mutable_loginrsp();
  logoutRsp->set_msgtype(protocol::csmsg::CSLoginMsgType::EN_PLAYER_LOGOUT);
  logoutRsp->set_issuccess(ssLogoutRsp.issuccess());
  if(logoutRsp->issuccess()) {
    activePlayers.erase(ssLogoutRsp.playerinfo().playername());
    playerIdToPlayerName.erase(ssLogoutRsp.playerinfo().playerid());
    std::cout << "Player logout success, player name: "
              << playerInfo.playername() << std::endl;
    logger->info("Player logout success, player name: {}",
                 playerInfo.playername());
  } else {
    std::cerr << "Player logout failed" << std::endl;
    logger->error("Player logout failed, player name: {}",
                  playerInfo.playername());
  }
  co_return;
}