#include <iostream>
#include <random>
#include <sstream>
#include <iomanip>
#pragma once

inline std::string generateUUID() {
    std::random_device rd;
    std::uniform_int_distribution<int> dist(0, 15);

    std::stringstream ss;
    ss << std::hex;
    for (int i = 0; i < 8; ++i) ss << dist(rd);
    ss << "-";
    for (int i = 0; i < 4; ++i) ss << dist(rd);
    ss << "-4"; // UUID version 4
    for (int i = 0; i < 3; ++i) ss << dist(rd);
    ss << "-";
    ss << dist(rd) % 4 + 8; // UUID variant
    for (int i = 0; i < 3; ++i) ss << dist(rd);
    ss << "-";
    for (int i = 0; i < 12; ++i) ss << dist(rd);

    return ss.str();
}