#!/bin/bash
IMAGE_NAME="team-14"
VERSION="1.0.0"

# Docker 이미지 빌드
sudo docker buildx build \
  --file Dockerfile.base \
  --platform linux/amd64 \
  --no-cache \
  -t amdp-registry.skala-ai.com/skala25a/${IMAGE_NAME}-data-base:${VERSION} --push .


sudo docker buildx build \
  --file Dockerfile \
  --platform linux/amd64 \
  --no-cache \
  -t amdp-registry.skala-ai.com/skala25a/${IMAGE_NAME}-data:${VERSION} --push .
