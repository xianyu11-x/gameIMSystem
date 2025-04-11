set_source_files_properties(${MSG_SRCS} PROPERTIES GENERATED TRUE)
set(SRC
    loginsvr.cpp
    loginServer.cpp
    ../util/server.cpp
    ../util/baseMsgHelper.cpp
    ../util/sendMsg.cpp
    ${MSG_SRCS}
    )
add_executable(loginsvr ${SRC})
add_dependencies(loginsvr generate_protocol)
target_link_libraries(loginsvr coroio ${PROTOBUF_LIBRARIES})