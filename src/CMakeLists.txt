#PROTOBUF生成
find_package(Protobuf REQUIRED)
set(PROTO_OUTDIR ${CMAKE_BINARY_DIR}/protocol)
if(EXISTS "${CMAKE_BINARY_DIR}/protocol" AND IS_DIRECTORY "${CMAKE_BINARY_DIR}/protocol")
    SET(PROTO_META_BASE_DIR ${PROTO_OUTDIR})
else()
    file(MAKE_DIRECTORY ${PROTO_OUTDIR})
    SET(PROTO_META_BASE_DIR ${PROTO_OUTDIR})
endif()
LIST(APPEND PROTO_FLAGS -I${CMAKE_SOURCE_DIR}/protocol)
file(GLOB_RECURSE MSG_PROTOS ${CMAKE_SOURCE_DIR}/protocol/*.proto)

set(MSG_SRCS "")
set(MSG_HDRS "")


message(STATUS "MSG_PROTOS: ${MSG_PROTOS}")

foreach(PROTO ${MSG_PROTOS})
    get_filename_component(PROTO_NAME ${PROTO} NAME_WE)
    get_filename_component(PROTO_DIR ${PROTO} DIRECTORY)
    file(RELATIVE_PATH REL_PROTO_DIR ${CMAKE_SOURCE_DIR}/protocol ${PROTO_DIR})
    set(PROTO_CC "${CMAKE_BINARY_DIR}/protocol/${REL_PROTO_DIR}/${PROTO_NAME}.pb.cc")
    set(PROTO_H "${CMAKE_BINARY_DIR}/protocol/${REL_PROTO_DIR}/${PROTO_NAME}.pb.h")
    file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/protocol/${REL_PROTO_DIR})
    list(APPEND MSG_SRCS "${PROTO_CC}")
    list(APPEND MSG_HDRS "${PROTO_H}")

    add_custom_command(
      OUTPUT "${PROTO_CC}"
             "${PROTO_H}"
      COMMAND  ${PROTOBUF_PROTOC_EXECUTABLE}
      ARGS --cpp_out  ${PROTO_META_BASE_DIR}
        -I ${CMAKE_SOURCE_DIR}/protocol
        ${PROTO}
      DEPENDS ${PROTO}
      COMMENT "Running C++ protocol buffer compiler on ${PROTO}"
      VERBATIM
    )
endforeach()

message(STATUS "MSG_SRCS: ${MSG_SRCS}")
set_source_files_properties(${MSG_SRCS} ${MSG_HDRS} PROPERTIES GENERATED TRUE)
add_custom_target(generate_protocol ALL
                DEPENDS ${MSG_SRCS} ${MSG_HDRS}
                COMMENT "generate message target"
                VERBATIM
                )


include_directories(${CMAKE_BINARY_DIR}/protocol)





#server构建
# add_subdirectory(chatsvr)
add_subdirectory(gatesvr)
# add_subdirectory(whispersvr)
add_subdirectory(loginsvr)


# set(SRC main.cpp
#         util/server.cpp)
# add_executable(test ${SRC})
# target_link_libraries(test coroio)


add_executable(client test/client.cpp util/baseMsgHelper.cpp ${MSG_SRCS})
target_link_libraries(client coroio ${PROTOBUF_LIBRARIES})
