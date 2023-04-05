#!/bin/bash

set -euo pipefail
DOCKER_BUILD_PLATFORM="${DOCKER_BUILD_PLATFORM:-linux/amd64}"
DOCKER_BUILD_REPOSITORY="${DOCKER_BUILD_REPOSITORY:-quay.io/unstructured-io/unstructured-api}"
PIPELINE_PACKAGE="general"
PIP_VERSION="${PIP_VERSION:-22.2.1}"
DOCKER_BUILD_IMAGE_NAME="${DOCKER_BUILD_IMAGE_NAME:-unstructured-api:dev}"

echo "Building for platform: $DOCKER_BUILD_PLATFORM"
echo "Using PIP_VERSION: $PIP_VERSION"
echo "Using PIPELINE_PACKAGE: $PIPELINE_PACKAGE"
echo "Using DOCKER_BUILD_REPOSITORY: $DOCKER_BUILD_REPOSITORY"

DOCKER_BUILD_CMD=(docker buildx build --load -f Dockerfile \
  --build-arg PIP_VERSION="$PIP_VERSION" \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --build-arg PIPELINE_PACKAGE="$PIPELINE_PACKAGE" \
  --progress plain \
  --cache-from "$DOCKER_BUILD_REPOSITORY":latest \
  -t "$DOCKER_BUILD_IMAGE_NAME" .)

# only build for specific platform if DOCKER_BUILD_PLATFORM is set
if [ -n "${DOCKER_BUILD_PLATFORM:-}" ]; then
  DOCKER_BUILD_CMD+=("--platform=$DOCKER_BUILD_PLATFORM")
fi

DOCKER_BUILDKIT=1 "${DOCKER_BUILD_CMD[@]}"