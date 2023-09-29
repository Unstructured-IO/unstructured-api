#!/usr/bin/env bash

UNSTRUCTURED_DOWNLOAD_CHIPPER=${UNSTRUCTURED_DOWNLOAD_CHIPPER:-"false"}

if [[ "$(echo "${UNSTRUCTURED_DOWNLOAD_CHIPPER}" | tr '[:upper:]' '[:lower:]')" == "true" ]]; then
  echo "warming chipper model"
  # NOTE(crag): in the cloud, this could add a minute to startup time
  UNSTRUCTURED_HI_RES_SUPPORTED_MODEL=chipper python3.8 -c \
    "from unstructured.ingest.doc_processor.generalized import initialize; initialize()"
fi

uvicorn prepline_general.api.app:app \
	--log-config logger_config.yaml \
        --host 0.0.0.0
