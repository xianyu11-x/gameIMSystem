#include <string>
#include <cstdlib>
#pragma once

class configManager {
public:
    static configManager& getInstance() {
        static configManager instance;
        return instance;
    }

    std::string getChatServerAddr() const {
        return getEnvOrDefault("CHAT_SERVER_ADDR", "0.0.0.0:10002");
    }

    std::string getChannelServerAddr() const {
        return getEnvOrDefault("CHANNEL_SERVER_ADDR", "0.0.0.0:10003");
    }

    std::string getLoginServerAddr() const {
        return getEnvOrDefault("LOGIN_SERVER_ADDR", "0.0.0.0:10001");
    }

    std::string getRedisAddr() const {
        return getEnvOrDefault("REDIS_ADDR", "0.0.0.0:6379");
    }

    std::string getGateServerAddr() const {
        return getEnvOrDefault("GATE_SERVER_ADDR", "0.0.0.0:8888");
    }

private:
    configManager() = default;

    std::string getEnvOrDefault(const std::string& envVar, const std::string& defaultValue) const {
        const char* value = std::getenv(envVar.c_str());
        return value ? std::string(value) : defaultValue;
    }
};