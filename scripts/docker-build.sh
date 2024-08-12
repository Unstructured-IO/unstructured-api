#!/usr/bin/env bash

set -euo pipefail
DOCKER_REPOSITORY="${DOCKER_REPOSITORY:-quay.io/unstructured-io/unstructured-api}"
PIPELINE_PACKAGE=${PIPELINE_PACKAGE:-"general"}
PIPELINE_FAMILY=${PIPELINE_FAMILY:-"general"}
PIP_VERSION="${PIP_VERSION:-22.2.1}"
DOCKER_IMAGE="${DOCKER_IMAGE:-pipeline-family-${PIPELINE_FAMILY}-dev}"
DOCKER_PLATFORM="linux/amd64"

DOCKER_BUILD_CMD=(
  docker buildx build --load -f Dockerfile
  --build-arg PIP_VERSION="$PIP_VERSION"
  --build-arg BUILDKIT_INLINE_CACHE=1
  --build-arg PIPELINE_PACKAGE="$PIPELINE_PACKAGE"
  --progress plain
  --platform linux/amd64
  --cache-from "$DOCKER_REPOSITORY:latest"
  -t "$DOCKER_IMAGE"
  .
)

# Set the platform using the DOCKER_PLATFORM environment variable
export DOCKER_DEFAULT_PLATFORM="$DOCKER_PLATFORM"

DOCKER_BUILDKIT=1 "${DOCKER_BUILD_CMD[@]}"