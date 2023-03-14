#!/bin/bash

# Run the container and send the sample images to it
# We can probably have a more generalized approach to smoke testing

container_name=pipeline-general

echo Starting container $container_name
docker run -p 8000:8000 -d --name $container_name --mount type=bind,source=$(realpath .),target=/home/notebook-user/local --rm pipeline-family-general-dev:latest --port 8000 --host 0.0.0.0

# TODO: We can be smarter about a readiness check
sleep 15

echo Running tests
PYTHONPATH=. pytest scripts/smoketest.py

echo Stopping container $container_name
docker stop $container_name
