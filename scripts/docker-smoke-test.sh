#!/bin/bash

# docker-smoke-test.sh
# Start the containerized api and run some end-to-end tests against it
# There will be some overlap with just running a TestClient in the unit tests
# Is there a good way to reuse code here?
# Also note this can evolve into a generalized pipeline smoke test

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

container_name=pipeline-general
image_name=pipeline-family-general-dev:latest

start_container() {
    echo Starting container "$container_name"
    docker run -p 8000:8000 -d --rm --name "$container_name" "$image_name" --port 8000 --host 0.0.0.0

    # Wait until the api is ready
    # We can be smarter here - wait until /healthcheck returns?
    sleep 15
}

stop_container() {
    echo Stopping container "$container_name"
    docker stop "$container_name"
}

start_container

echo Running tests
PYTHONPATH=. pytest scripts/smoketest.py

# Regardless of test result, stop the container
result=$?
trap stop_container EXIT
exit $result
