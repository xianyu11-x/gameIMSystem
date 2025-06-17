#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <netdb.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <cstring>
#pragma once
inline std::pair<std::string,int> parseAddress(const std::string& address){
    std::vector<std::string> result;
    std::stringstream ss(address);
    std::string token;

    while (std::getline(ss, token, ':')) {
        result.push_back(token);
    }
    if(result.size() != 2){
        return {"",-1};
    }
    return {result[0],std::stoi(result[1])};
}

inline std::vector<std::string> resolveAllAddresses(const std::string& address) {
    std::vector<std::string> addresses;
    struct addrinfo hints, *result, *rp;
    char ip_str[INET6_ADDRSTRLEN];
    
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_ADDRCONFIG;
    
    int status = getaddrinfo(address.c_str(), nullptr, &hints, &result);
    if (status != 0) {
        std::cout << "getaddrinfo error: " << gai_strerror(status) << std::endl;
        return addresses;
    }
    
    // 遍历所有结果
    for (rp = result; rp != nullptr; rp = rp->ai_next) {
        void* addr;
        
        if (rp->ai_family == AF_INET) {
            struct sockaddr_in* ipv4 = (struct sockaddr_in*)rp->ai_addr;
            addr = &(ipv4->sin_addr);
        } else if (rp->ai_family == AF_INET6) {
            struct sockaddr_in6* ipv6 = (struct sockaddr_in6*)rp->ai_addr;
            addr = &(ipv6->sin6_addr);
        } else {
            continue;
        }
        
        if (inet_ntop(rp->ai_family, addr, ip_str, INET6_ADDRSTRLEN) != nullptr) {
            addresses.emplace_back(ip_str);
        }
    }
    
    freeaddrinfo(result);
    return addresses;
}

inline std::string resolveAddress(const std::string& address) {
    auto res = resolveAllAddresses(address);
    if (res.empty()) {
        throw std::runtime_error("No valid addresses found for " + address);
    }
    return res.front();
}