#include "gateServer.h"
#include "spdlog/spdlog.h"
int main(){
    NNet::TLoop<NNet::TEPoll> loop;
    std::cout<<"start gate server"<<std::endl;
    gateServer server(loop.Poller(),"127.0.0.1:8888", 128);
    spdlog::get("gateSvrLogger")->info("Gate server started");
    server.start();
    loop.Loop();
    return 0;
}