set_source_files_properties(${MSG_SRCS} PROPERTIES GENERATED TRUE)
file(GLOB_RECURSE SVR_ACTION action/*.cpp)
set(SRC
    gate.cpp
    gateServer.cpp
    ../util/server.cpp
    ../util/baseMsgHelper.cpp
    ../util/sendMsg.cpp
    ../loginsvr/sdk/sendLoginMsg.cpp
    ../loginsvr/sdk/sendLogoutMsg.cpp
    ../chatsvr/sdk/sendChatMsg.cpp
    ${SVR_ACTION}
    ${MSG_SRCS}
    )
add_executable(gatesvr ${SRC})
add_dependencies(gatesvr generate_protocol)

# =============================================================================
# Link libraries using modern CMake targets
# =============================================================================
target_link_libraries(gatesvr 
    PRIVATE
        coroio
        ${PROTOBUF_LIBRARIES}
        spdlog::spdlog
)