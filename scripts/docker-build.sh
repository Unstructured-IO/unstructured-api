#!/usr/bin/env bash

set -euo pipefail
DOCKER_REPOSITORY="${DOCKER_REPOSITORY:-quay.io/unstructured-io/unstructured-api}"
PIPELINE_PACKAGE=${PIPELINE_PACKAGE:-"general"}
PIPELINE_FAMILY=${PIPELINE_FAMILY:-"general"}
DOCKER_IMAGE="${DOCKER_IMAGE:-pipeline-family-${PIPELINE_FAMILY}-dev}"
DOCKER_PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"


DOCKER_BUILD_CMD=(
  docker buildx build --load -f Dockerfile
  --build-arg BUILDKIT_INLINE_CACHE=1
  --build-arg PIPELINE_PACKAGE="$PIPELINE_PACKAGE"
  --progress plain
  --platform "$DOCKER_PLATFORM"
  --cache-from "$DOCKER_REPOSITORY:latest"
  -t "$DOCKER_IMAGE"
  .
)

DOCKER_BUILDKIT=1 "${DOCKER_BUILD_CMD[@]}"
