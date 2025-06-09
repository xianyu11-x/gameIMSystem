#include "chatServer.h"
#include "spdlog/spdlog.h"
int main(){
    NNet::TLoop<NNet::TEPoll> loop;
    std::cout<<"start chat server"<<std::endl;
    chatServer server(loop.Poller(),"127.0.0.1:10002", 1024);
    spdlog::get("chatSvrLogger")->info("Chat server started");
    server.start();
    loop.Loop();
    return 0;
}