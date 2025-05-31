set_source_files_properties(${MSG_SRCS} PROPERTIES GENERATED TRUE)
file(GLOB_RECURSE SVR_ACTION action/*.cpp)
set(SRC
    chatsvr.cpp
    chatServer.cpp
    ../util/server.cpp
    ../util/baseMsgHelper.cpp
    ../util/sendMsg.cpp
    ${SVR_ACTION}
    ${MSG_SRCS}
    )
add_executable(chatsvr ${SRC})
add_dependencies(chatsvr generate_protocol)

# =============================================================================
# Link libraries using modern CMake targets
# =============================================================================
target_link_libraries(chatsvr 
    PRIVATE
        coroio
        ${PROTOBUF_LIBRARIES}
        spdlog::spdlog
        redis++::redis++
)