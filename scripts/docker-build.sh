#!/bin/bash

set -euo pipefail

DOCKER_BUILDKIT=1 docker buildx build --platform=linux/amd64 -f docker/Dockerfile"${BUILD_TYPE}" \
  --build-arg PIP_VERSION="$PIP_VERSION" \
  --build-arg PIPELINE_FAMILY="$PIPELINE_FAMILY" \
  --progress plain \
  -t pipeline-family-"$PIPELINE_FAMILY"-dev"${BUILD_TYPE}":latest .
