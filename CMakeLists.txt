cmake_minimum_required(VERSION 3.16)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

project(gameIMSystem LANGUAGES CXX)


if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Choose Release or Debug" FORCE)
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release" "RelWithDebInfo" "MinSizeRel")
endif()
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")


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


message(STATUS "Building spdlog...")
set(SPDLOG_BUILD_SHARED OFF CACHE BOOL "Build shared library" FORCE)
set(SPDLOG_BUILD_EXAMPLE OFF CACHE BOOL "Build example" FORCE)
set(SPDLOG_BUILD_TESTS OFF CACHE BOOL "Build tests" FORCE)
set(SPDLOG_INSTALL OFF CACHE BOOL "Generate install target" FORCE)
add_subdirectory(third_party/spdlog)


message(STATUS "Building hiredis...")
set(BUILD_SHARED_LIBS OFF CACHE BOOL "Build shared libraries" FORCE)
set(ENABLE_SSL OFF CACHE BOOL "Enable SSL support" FORCE)
set(DISABLE_TESTS ON CACHE BOOL "Disable tests" FORCE)
set(ENABLE_EXAMPLES OFF CACHE BOOL "Enable examples" FORCE)
add_subdirectory(third_party/hiredis)


message(STATUS "Building redis-plus-plus...")
set(REDIS_PLUS_PLUS_BUILD_STATIC ON CACHE BOOL "Build static library" FORCE)
set(REDIS_PLUS_PLUS_BUILD_SHARED OFF CACHE BOOL "Build shared library" FORCE)
set(REDIS_PLUS_PLUS_BUILD_TEST OFF CACHE BOOL "Build tests" FORCE)
set(REDIS_PLUS_PLUS_USE_TLS OFF CACHE BOOL "Build with TLS support" FORCE)
set(REDIS_PLUS_PLUS_CXX_STANDARD 17 CACHE STRING "CXX standard" FORCE)


# Create a hiredis config to help redis-plus-plus find hiredis
# Set variables that redis-plus-plus CMakeLists.txt looks for
set(CMAKE_DISABLE_FIND_PACKAGE_hiredis TRUE)
set(hiredis_FOUND TRUE CACHE BOOL "Force use custom hiredis settings" FORCE)
set(hiredis_INCLUDE_DIRS ${CMAKE_CURRENT_SOURCE_DIR}/third_party CACHE STRING "hiredis include dirs" FORCE)
set(HIREDIS_HEADER "${CMAKE_SOURCE_DIR}/third_party" CACHE PATH "hiredis header path" FORCE)
set(HIREDIS_LIB hiredis CACHE STRING "hiredis library target" FORCE)
set(REDIS_PLUS_PLUS_HIREDIS_LIBS "hiredis::hiredis" CACHE STRING "hiredis libs" FORCE)
set(REDIS_PLUS_PLUS_HIREDIS_LIBS_STATIC "hiredis::hiredis" CACHE STRING "hiredis static libs" FORCE)
add_subdirectory(third_party/redis-plus-plus)


message(STATUS "Building coroio...")
add_subdirectory(third_party/coroio)


message(STATUS "=== Third-party Dependencies Built ===")


if(NOT TARGET spdlog::spdlog)
    message(FATAL_ERROR "spdlog target not found")
endif()

if(NOT TARGET hiredis::hiredis)
    message(FATAL_ERROR "hiredis target not found")  
endif()

if(NOT TARGET redis++::redis++_static)
    message(FATAL_ERROR "redis++ target not found")
endif()

if(NOT TARGET coroio)
    message(FATAL_ERROR "coroio target not found")
endif()

# =============================================================================
# Project source code
# =============================================================================
add_subdirectory(src)

