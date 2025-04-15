#include "common/SSMsg.pb.h"
#include "gatesvr/gateServer.h"
#include "loginsvr/sdk/sendLogoutMsg.h"

TFuture<void> gateServer::csLogout(const int socketFd,
                                   const std::string &message,
                                   std::string &response) {
  protocol::common::PlayerInfo playerInfo;
  if (!playerInfo.ParseFromString(message)) {
    std::cerr << "Failed to parse player info" << std::endl;
    co_return;
  }
  std::string curPlayerName = playerInfo.playername();
  if (activePlayers.find(curPlayerName) == activePlayers.end()) {
    std::cerr << "Player already logged out" << std::endl;
    // co_await activePlayers[curPlayerName]->WriteSome("Player already logged
    // in", 24);
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
    std::cout << "Player logout success, player name: "
              << playerInfo.playername() << std::endl;
  } else {
    std::cerr << "Player logout failed" << std::endl;
  }
  co_return;
}