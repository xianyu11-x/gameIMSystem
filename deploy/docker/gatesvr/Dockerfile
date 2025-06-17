# docker/gatesvr/Dockerfile
FROM ubuntu:24.04

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libprotobuf-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /app

# 复制二进制文件和依赖库
COPY bin/gatesvr /app/
COPY lib/ /app/lib/

# 创建日志目录
RUN mkdir -p /app/logs

# 设置环境变量
ENV LD_LIBRARY_PATH=/app/lib

# 暴露端口
EXPOSE 8888

# 启动命令
CMD ["./gatesvr"]