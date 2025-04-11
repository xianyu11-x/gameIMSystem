#include <sstream>
#include <string>
#include <vector>
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