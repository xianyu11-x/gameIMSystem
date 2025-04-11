#include "gateServer.h"

int main(){
    NNet::TLoop<NNet::TEPoll> loop;
    std::cout<<"start login server"<<std::endl;
    gateServer server(loop.Poller(),"127.0.0.1:8888", 128);
    server.start();
    loop.Loop();
    return 0;
}