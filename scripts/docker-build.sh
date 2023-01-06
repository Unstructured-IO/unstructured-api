#!/bin/bash

set -euo pipefail

DOCKER_BUILDKIT=1 docker buildx build --platform=linux/amd64 -f Dockerfile \
  --build-arg PIP_VERSION="$PIP_VERSION" \
  --build-arg PIPELINE_PACKAGE="$PIPELINE_PACKAGE" \
  --progress plain \
  -t pipeline-family-"$PIPELINE_FAMILY"-dev:latest .
