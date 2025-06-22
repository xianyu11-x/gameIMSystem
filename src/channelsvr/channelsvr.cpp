#include "channelServer.h"
#include "spdlog/spdlog.h"
int main(){
    NNet::TLoop<NNet::TUring> loop;
    std::cout<<"start channel server"<<std::endl;
    channelServer server(loop.Poller(),"0.0.0.0:10003", 1024);
    spdlog::get("channelSvrLogger")->info("Channel server started");
    server.start();
    loop.Loop();
    return 0;
}