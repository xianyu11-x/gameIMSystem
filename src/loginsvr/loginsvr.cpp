#include "loginServer.h"
#include "spdlog/spdlog.h"
int main(){
    NNet::TLoop<NNet::TUring> loop;
    std::cout<<"start login server"<<std::endl;
    loginServer server(loop.Poller(),"0.0.0.0:10001", 1024);
    spdlog::get("loginSvrLogger")->info("Login server started");
    server.start();
    loop.Loop();
    return 0;
}