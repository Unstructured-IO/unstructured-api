#!/bin/bash

set -euo pipefail
DOCKER_BUILD_PLATFORM="${DOCKER_BUILD_PLATFORM:-linux/amd64}"
DOCKER_BUILD_REPOSITORY="${DOCKER_BUILD_REPOSITORY:-quay.io/unstructured-io/unstructured-api}"
PIPELINE_PACKAGE="${PIPELINE_PACKAGE:-general}"
PIP_VERSION="${PIP_VERSION:-21.0.1}"

DOCKER_BUILDKIT=1 docker buildx build --load --platform="$DOCKER_BUILD_PLATFORM" -f Dockerfile \
  --build-arg PIP_VERSION="$PIP_VERSION" \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --build-arg PIPELINE_PACKAGE="$PIPELINE_PACKAGE" \
  --progress plain \
  --cache-from "$DOCKER_BUILD_REPOSITORY":latest \
  -t pipeline-family-"$PIPELINE_FAMILY"-dev:latest .
