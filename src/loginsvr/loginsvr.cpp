#include "loginServer.h"

int main(){
    NNet::TLoop<NNet::TEPoll> loop;
    std::cout<<"start login server"<<std::endl;
    loginServer server(loop.Poller(),"127.0.0.1:10001", 128);
    server.start();
    loop.Loop();
    return 0;
}