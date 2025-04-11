set_source_files_properties(${MSG_SRCS} PROPERTIES GENERATED TRUE)
set(SRC
    gate.cpp
    gateServer.cpp
    ../util/server.cpp
    ../util/baseMsgHelper.cpp
    ../util/sendMsg.cpp
    action/csLogin.cpp
    ${MSG_SRCS}
    )
add_executable(gatesvr ${SRC})
add_dependencies(gatesvr generate_protocol)
target_link_libraries(gatesvr coroio ${PROTOBUF_LIBRARIES})