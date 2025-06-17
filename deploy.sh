#!/bin/bash

echo "开始部署到Kubernetes..."

echo "构建Docker镜像..."
eval $(minikube docker-env)

docker build -t game-im/gatesvr:latest -f deploy/docker/gatesvr/Dockerfile .
docker build -t game-im/chatsvr:latest -f deploy/docker/chatsvr/Dockerfile .
docker build -t game-im/channelsvr:latest -f deploy/docker/channelsvr/Dockerfile .
docker build -t game-im/loginsvr:latest -f deploy/docker/loginsvr/Dockerfile .


echo "部署到Kubernetes..."
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/redis/
kubectl apply -f deploy/k8s/gatesvr/
kubectl apply -f deploy/k8s/chatsvr/
kubectl apply -f deploy/k8s/channelsvr/
kubectl apply -f deploy/k8s/loginsvr/

echo "等待服务启动..."
kubectl wait --for=condition=ready pod -l app=redis -n game-im-system --timeout=60s
kubectl wait --for=condition=ready pod -l app=gatesvr -n game-im-system --timeout=60s

echo "部署完成！"
echo "访问地址: http://$(minikube ip):30888"