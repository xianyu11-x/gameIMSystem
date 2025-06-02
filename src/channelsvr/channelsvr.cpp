#include "channelServer.h"
#include "spdlog/spdlog.h"
int main(){
    NNet::TLoop<NNet::TEPoll> loop;
    std::cout<<"start whisper server"<<std::endl;
    channelServer server(loop.Poller(),"127.0.0.1:10002", 128);
    spdlog::get("whisperSvrLogger")->info("Login server started");
    server.start();
    loop.Loop();
    return 0;
}