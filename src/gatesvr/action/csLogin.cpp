#include "common/BaseMsg.pb.h"
#include "common/SSMsg.pb.h"
#include "gatesvr/gateServer.h"
#include "loginsvr/sdk/sendLoginMsg.h"
#include "util/sendMsg.h"
#include <sys/socket.h>

TFuture<void> gateServer::csLogin(const int socketFd,
                                  const std::string &message,
                                  std::string &response) {
  protocol::common::PlayerInfo playerInfo;
  if (!playerInfo.ParseFromString(message)) {
    std::cerr << "Failed to parse login player" << std::endl;
    logger->error("Failed to parse login player");
    co_return;
  }

  auto curPlayerName = playerInfo.playername();
  if (activePlayers.find(curPlayerName) != activePlayers.end()) {
    std::cerr << "Player already logged in" << std::endl;
    logger->warn("Player already logged in, player name: {}",
                 playerInfo.playername());
    co_return;
  }

  // TODO:向实际loginsvr发送登录请求
  auto rspStr =
      co_await sendLoginMsg(serverPoller, curPlayerName,
                            protocol::common::MsgSender::EN_MSG_SENDER_GATESVR);
  protocol::ssmsg::SSMsgRsp rsp;
  rsp.ParseFromString(rspStr);
  auto ssLoginRsp = rsp.loginrsp();

  protocol::csmsg::CSMsgRsp csRsp;
  csRsp.set_msgtype(protocol::csmsg::CSMsgType::EN_LOGIN);
  auto loginRsp = csRsp.mutable_loginrsp();
  loginRsp->set_msgtype(protocol::csmsg::CSLoginMsgType::EN_PLAYER_LOGIN);
  auto loginedPlayer = loginRsp->mutable_info();
  // 目前简单返回一下
  loginedPlayer->set_playertoken(ssLoginRsp.playerinfo().playertoken());
  loginedPlayer->set_playername(ssLoginRsp.playerinfo().playername());
  loginedPlayer->set_playerid(ssLoginRsp.playerinfo().playerid());
  loginRsp->set_issuccess(ssLoginRsp.issuccess());

  if (loginRsp->issuccess()) {
    auto it = connectedClients.find(socketFd);
    if (it != connectedClients.end()) {
      activePlayers.insert({playerInfo.playername(), it->second});
      playerIdToPlayerName.insert(
          {playerInfo.playerid(), playerInfo.playername()});
    }
    std::cout << "Player login success, player name: "
              << playerInfo.playername() << std::endl;
    logger->info("Player login success, player name: {}",
                 playerInfo.playername());
  } else {
  }
  response = csRsp.SerializeAsString();

  co_return;
}