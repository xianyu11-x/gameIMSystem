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
target_link_libraries(chatsvr coroio ${PROTOBUF_LIBRARIES} spdlog::spdlog $<$<BOOL:${MINGW}>:ws2_32>)
find_path(HIREDIS_HEADER hiredis)
target_include_directories(chatsvr PUBLIC ${HIREDIS_HEADER})

find_library(HIREDIS_LIB hiredis)
target_link_libraries(chatsvr ${HIREDIS_LIB})

# <------------ add redis-plus-plus dependency -------------->
# NOTE: this should be *sw* NOT *redis++*
find_path(REDIS_PLUS_PLUS_HEADER sw)
target_include_directories(chatsvr PUBLIC ${REDIS_PLUS_PLUS_HEADER})

find_library(REDIS_PLUS_PLUS_LIB redis++)
target_link_libraries(chatsvr ${REDIS_PLUS_PLUS_LIB})