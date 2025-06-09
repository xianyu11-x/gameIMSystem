#include "channelServer.h"
#include "spdlog/spdlog.h"
int main(){
    NNet::TLoop<NNet::TEPoll> loop;
    std::cout<<"start channel server"<<std::endl;
    channelServer server(loop.Poller(),"127.0.0.1:10003", 1024);
    spdlog::get("channelSvrLogger")->info("Channel server started");
    server.start();
    loop.Loop();
    return 0;
}