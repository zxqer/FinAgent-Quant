cmake_minimum_required(VERSION 3.10)

# 项目名称
project(FinAgent_DataProvider LANGUAGES CXX)

# 强制使用 C++17 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- 1. 寻找依赖库 ---
# 使用 Module 模式寻找 Protobuf，这是 Ubuntu 环境下最稳健的方式
find_package(Threads REQUIRED)
find_package(Protobuf REQUIRED)
# gRPC 依然使用 CONFIG 模式，因为它通常提供标准的 CMake 导出文件
find_package(gRPC CONFIG REQUIRED)

message(STATUS "Found Protobuf: ${Protobuf_LIBRARIES}")
message(STATUS "Using gRPC ${gRPC_VERSION}")

# --- 2. 路径设置 (核心修复：全部使用绝对路径) ---

# 指向项目根目录下的 proto 文件夹
set(PROTO_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../proto")
set(PROTO_SRC "${PROTO_DIR}/fin_agent.proto")

# 将生成的代码放在当前 build 目录下的 generated 子目录中，避免权限问题
set(PROTO_GEN_DIR "${PROJECT_BINARY_DIR}/generated")
if(NOT EXISTS "${PROTO_GEN_DIR}")
    file(MAKE_DIRECTORY "${PROTO_GEN_DIR}")
endif()

# --- 3. 处理 gRPC / Protobuf 自动生成 ---

# 寻找编译器程序
find_program(_PROTOBUF_PROTOC protoc)
find_program(_GRPC_CPP_PLUGIN_EXECUTABLE grpc_cpp_plugin)

# 预定义生成的文件列表
set(GRPC_SRCS 
    "${PROTO_GEN_DIR}/fin_agent.pb.cc"
    "${PROTO_GEN_DIR}/fin_agent.pb.h"
    "${PROTO_GEN_DIR}/fin_agent.grpc.pb.cc"
    "${PROTO_GEN_DIR}/fin_agent.grpc.pb.h"
)

# 自动化构建指令
add_custom_command(
    OUTPUT ${GRPC_SRCS}
    COMMAND ${_PROTOBUF_PROTOC}
    ARGS --cpp_out "${PROTO_GEN_DIR}"
         --grpc_out "${PROTO_GEN_DIR}"
         --plugin=protoc-gen-grpc=${_GRPC_CPP_PLUGIN_EXECUTABLE}
         -I "${PROTO_DIR}"
         "${PROTO_SRC}"
    DEPENDS "${PROTO_SRC}"
    COMMENT "Generating gRPC/Protobuf C++ sources from ${PROTO_SRC}"
    VERBATIM
)

# --- 4. 定义可执行文件 ---

# 编译主程序，并包含生成的源文件
add_executable(data_provider 
    src/main.cpp 
    ${GRPC_SRCS}
)

# --- 5. 配置包含路径与链接库 ---

# 包含生成的头文件目录和本项目 include 目录
target_include_directories(data_provider PRIVATE 
    "${PROTO_GEN_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

# 链接对应的库
target_link_libraries(data_provider
    gRPC::grpc++
    ${Protobuf_LIBRARIES}
    Threads::Threads
)

# --- 6. 编译选项 (工业级规范) ---
if(NOT MSVC)
    target_compile_options(data_provider PRIVATE -Wall -Wextra -O3)
endif()