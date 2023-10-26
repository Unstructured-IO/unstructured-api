#!/usr/bin/env bash

uvicorn prepline_general.api.app:app \
	--log-config logger_config.yaml \
        --host 0.0.0.0
