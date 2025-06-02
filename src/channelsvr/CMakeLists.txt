set_source_files_properties(${MSG_SRCS} PROPERTIES GENERATED TRUE)
file(GLOB_RECURSE SVR_ACTION action/*.cpp)
set(SRC
    channelsvr.cpp
    channelServer.cpp
    ../util/server.cpp
    ../util/baseMsgHelper.cpp
    ../util/sendMsg.cpp
    ${SVR_ACTION}
    ${MSG_SRCS}
    )
add_executable(channelsvr ${SRC})
add_dependencies(channelsvr generate_protocol)

# =============================================================================
# Link libraries using modern CMake targets
# =============================================================================
target_link_libraries(channelsvr 
    PRIVATE
        coroio
        ${PROTOBUF_LIBRARIES}
        spdlog::spdlog
        redis++::redis++
)