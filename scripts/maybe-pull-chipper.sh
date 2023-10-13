#!/usr/bin/env bash

if [ -n "$UNSTRUCTURED_HF_TOKEN" ]; then
    echo Preloading Chipper model...
  UNSTRUCTURED_HI_RES_SUPPORTED_MODEL=chipper python3.10 -c \
    "from unstructured.ingest.pipeline.initialize import initialize; initialize()"
fi
