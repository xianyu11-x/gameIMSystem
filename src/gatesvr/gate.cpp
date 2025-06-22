#include "gateServer.h"
#include "spdlog/spdlog.h"
int main(){
    NNet::TLoop<NNet::TUring> loop;
    std::cout<<"start gate server"<<std::endl;
    gateServer server(loop.Poller(),"0.0.0.0:8888", 1024);
    spdlog::get("gateSvrLogger")->info("Gate server started");
    server.start();
    loop.Loop();
    return 0;
}