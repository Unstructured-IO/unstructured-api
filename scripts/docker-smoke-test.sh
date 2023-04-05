#!/bin/bash

# docker-smoke-test.sh
# Start the containerized api and run some end-to-end tests against it
# There will be some overlap with just running a TestClient in the unit tests
# Is there a good way to reuse code here?
# Also note this can evolve into a generalized pipeline smoke test

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

CONTAINER_NAME=unstructured-api-smoke-test
IMAGE_NAME="${IMAGE_NAME:-unstructured-api:dev}"
SKIP_INFERENCE_TESTS="${SKIP_INFERENCE_TESTS:-false}"

start_container() {
    echo Starting container "$CONTAINER_NAME"
    docker run -p 8000:8000 -d --rm --name "$CONTAINER_NAME" "$IMAGE_NAME" --port 8000 --host 0.0.0.0
}

await_server_ready() {
    url=localhost:8000/healthcheck

    # NOTE(rniko): Increasing the timeout to 120 seconds because emulated arm tests are slow to start
    for _ in {1..120}; do
        echo Waiting for response from "$url"
        if curl $url 2> /dev/null; then
            echo
            return
        fi

        sleep 1
    done

    echo Server did not respond!
    exit 1
}

stop_container() {
    echo Stopping container "$CONTAINER_NAME"
    docker stop "$CONTAINER_NAME"
}

start_container

# Regardless of test result, stop the container
trap stop_container EXIT

await_server_ready

echo Running tests
PYTHONPATH=. SKIP_INFERENCE_TESTS=$SKIP_INFERENCE_TESTS pytest scripts/smoketest.py

result=$?
exit $result
