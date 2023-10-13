#!/usr/bin/env bash

set -euo pipefail
DOCKER_REPOSITORY="${DOCKER_REPOSITORY:-quay.io/unstructured-io/unstructured-api}"
PIPELINE_PACKAGE=${PIPELINE_PACKAGE:-"general"}
PIPELINE_FAMILY=${PIPELINE_FAMILY:-"general"}
PIP_VERSION="${PIP_VERSION:-22.2.1}"
DOCKER_IMAGE="${DOCKER_IMAGE:-pipeline-family-${PIPELINE_FAMILY}-dev}"
DOCKER_PLATFORM="${DOCKER_PLATFORM:-}"


DOCKER_BUILD_CMD=(docker buildx build --load -f Dockerfile \
  --build-arg PIP_VERSION="$PIP_VERSION" \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --build-arg PIPELINE_PACKAGE="$PIPELINE_PACKAGE" \
  --progress plain \
  --target code \
  --cache-from "$DOCKER_REPOSITORY":latest \
  -t "$DOCKER_IMAGE")

# If a token is present to download Chipper, pass it in as a secret file
if [ -f hf_token ]; then
  # --secret id=hf_token,src=env_file \
  DOCKER_BUILD_CMD+=("--secret" "id=hf_token,src=hf_token")
fi

# only build for specific platform if DOCKER_PLATFORM is set
if [ -n "${DOCKER_PLATFORM:-}" ]; then
  DOCKER_BUILD_CMD+=("--platform=$DOCKER_PLATFORM")
fi

DOCKER_BUILDKIT=1 "${DOCKER_BUILD_CMD[@]}" .
