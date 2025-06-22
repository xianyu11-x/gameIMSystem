cmake_minimum_required(VERSION 3.16)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

project(gameIMSystem LANGUAGES CXX)


if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Choose Release or Debug" FORCE)
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release" "RelWithDebInfo" "MinSizeRel")
endif()
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")

# =============================================================================
# 调试配置
# =============================================================================
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    message(STATUS "=== Configuring Debug Build ===")
    
    # 详细的调试信息配置
    set(CMAKE_CXX_FLAGS_DEBUG "-g3 -gdwarf-4 -O0")
    
    # 保留栈帧信息，对协程调试很重要
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -fno-omit-frame-pointer")
    
    # 禁止内联和尾调用优化，确保调试准确性
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -fno-inline -fno-optimize-sibling-calls")
    
    # 添加更多运行时检查
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -fstack-protector-strong")
    
    # 可选：启用AddressSanitizer (取消注释以启用)
    # set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -fsanitize=address -fsanitize=undefined")
    # set(CMAKE_EXE_LINKER_FLAGS_DEBUG "${CMAKE_EXE_LINKER_FLAGS_DEBUG} -fsanitize=address -fsanitize=undefined")
    
    message(STATUS "Debug flags: ${CMAKE_CXX_FLAGS_DEBUG}")
    message(STATUS "=== Debug Configuration Complete ===")
endif()

if(CMAKE_BUILD_TYPE STREQUAL "Release")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -Wno-restrict")
endif()

if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fcoroutines")
    if (CMAKE_CXX_COMPILER_VERSION MATCHES "12.*")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-maybe-uninitialized")
    endif()
endif()
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)



set(CMAKE_RUNTIME_OUTPUT_DIRECTORY  ${CMAKE_SOURCE_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY  ${CMAKE_SOURCE_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY  ${CMAKE_SOURCE_DIR}/lib)


#include_directories(${CMAKE_SOURCE_DIR}/include)
include_directories(${CMAKE_SOURCE_DIR}/src)

# =============================================================================
# 第三方库构建
# =============================================================================
message(STATUS "=== Building Third-party Dependencies ===")
include(ExternalProject)

message(STATUS "Building spdlog...")
set(SPDLOG_BUILD_SHARED OFF CACHE BOOL "Build shared library" FORCE)
set(SPDLOG_BUILD_EXAMPLE OFF CACHE BOOL "Build example" FORCE)
set(SPDLOG_BUILD_TESTS OFF CACHE BOOL "Build tests" FORCE)
set(SPDLOG_INSTALL OFF CACHE BOOL "Generate install target" FORCE)
add_subdirectory(third_party/spdlog)

message(STATUS "Building hiredis...")
ExternalProject_Add(hiredis_external
    SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/hiredis
    CMAKE_ARGS 
        -DCMAKE_INSTALL_PREFIX=${CMAKE_CURRENT_SOURCE_DIR}/lib/hiredis
        -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
        -DBUILD_SHARED_LIBS=OFF
        -DENABLE_SSL=OFF
        -DDISABLE_TESTS=ON
    INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/lib/hiredis
)

message(STATUS "Building redis-plus-plus...")
ExternalProject_Add(redis++_external
    SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/redis-plus-plus
    CMAKE_ARGS 
        -DCMAKE_INSTALL_PREFIX=${CMAKE_CURRENT_SOURCE_DIR}/lib/redis-plus-plus
        -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
        -DCMAKE_PREFIX_PATH=${CMAKE_CURRENT_SOURCE_DIR}/lib/hiredis
        -DREDIS_PLUS_PLUS_BUILD_STATIC=ON
        -DREDIS_PLUS_PLUS_BUILD_SHARED=OFF
        -DREDIS_PLUS_PLUS_BUILD_TEST=OFF
        -DREDIS_PLUS_PLUS_USE_TLS=OFF
        -DREDIS_PLUS_PLUS_CXX_STANDARD=20
    INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/lib/redis-plus-plus
    DEPENDS hiredis_external
)


message(STATUS "Building coroio...")
add_subdirectory(third_party/coroio)


message(STATUS "=== Third-party Dependencies Built ===")

set(HIREDIS_ROOT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/lib/hiredis")
set(REDIS_PLUS_PLUS_ROOT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/lib/redis-plus-plus")

file(MAKE_DIRECTORY "${HIREDIS_ROOT_DIR}/include")
file(MAKE_DIRECTORY "${REDIS_PLUS_PLUS_ROOT_DIR}/include")

message(STATUS "Creating imported targets...")

add_library(hiredis::hiredis STATIC IMPORTED)
set_target_properties(hiredis::hiredis PROPERTIES
    IMPORTED_LOCATION "${HIREDIS_ROOT_DIR}/lib/libhiredisd.a"
    INTERFACE_INCLUDE_DIRECTORIES "${HIREDIS_ROOT_DIR}/include"
)
add_dependencies(hiredis::hiredis hiredis_external)

add_library(redis++::redis++ STATIC IMPORTED)
set_target_properties(redis++::redis++ PROPERTIES
    IMPORTED_LOCATION "${REDIS_PLUS_PLUS_ROOT_DIR}/lib/libredis++.a"
    INTERFACE_INCLUDE_DIRECTORIES "${REDIS_PLUS_PLUS_ROOT_DIR}/include"
    INTERFACE_LINK_LIBRARIES "hiredis::hiredis"
)
add_dependencies(redis++::redis++ redis++_external)

# 验证目标是否存在
if(NOT TARGET spdlog::spdlog)
    message(FATAL_ERROR "spdlog target not found")
endif()

if(NOT TARGET coroio)
    message(FATAL_ERROR "coroio target not found")
endif()

message(STATUS "All targets created successfully")

# =============================================================================
# 项目构建
# =============================================================================
add_subdirectory(src)

