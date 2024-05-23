#!/usr/bin/env bash


# docker-smoke-test.sh
# Start the containerized api and run some end-to-end tests against it
# There will be some overlap with just running a TestClient in the unit tests
# Is there a good way to reuse code here?
# Also note this can evolve into a generalized pipeline smoke test

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

set -e

CONTAINER_NAME=unstructured-api-smoke-test
CONTAINER_NAME_PARALLEL=unstructured-api-smoke-test-parallel
PIPELINE_FAMILY=${PIPELINE_FAMILY:-"general"}
DOCKER_IMAGE="${DOCKER_IMAGE:-pipeline-family-${PIPELINE_FAMILY}-dev:latest}"
SKIP_INFERENCE_TESTS="${SKIP_INFERENCE_TESTS:-false}"

start_container() {

    port=$1
    use_parallel_mode=$2

    if [ "$use_parallel_mode" = "true" ]; then
        name=$CONTAINER_NAME_PARALLEL
    else
        name=$CONTAINER_NAME
    fi

    echo Starting container "$name"
    docker run -p "$port":"$port" \
	   --entrypoint uvicorn \
           -d \
           --rm \
           --name "$name" \
           --env "UNSTRUCTURED_PARALLEL_MODE_URL=http://localhost:$port/general/v0/general" \
           --env "UNSTRUCTURED_PARALLEL_MODE_ENABLED=$use_parallel_mode" \
           "$DOCKER_IMAGE" \
           prepline_general.api.app:app --port "$port" --host 0.0.0.0
}

await_server_ready() {
    port=$1
    url=localhost:$port/healthcheck

    # NOTE(rniko): Increasing the timeout to 120 seconds because emulated arm tests are slow to start
    for _ in {1..120}; do
        echo Waiting for response from "$url"
        if curl "$url" 2> /dev/null; then
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
    # Note (austin) - if you're getting an error from the api, try dumping the logs
    # docker logs $CONTAINER_NAME 2> docker_logs.txt
    docker stop "$CONTAINER_NAME" 2> /dev/null || true

    echo Stopping container "$CONTAINER_NAME_PARALLEL"
    docker stop "$CONTAINER_NAME_PARALLEL" 2> /dev/null || true
}

# Always clean up the container
trap stop_container EXIT

start_container 8000 "false"
await_server_ready 8000

#######################
# Smoke Tests
#######################
echo Running smoke tests with SKIP_INFERENCE_TESTS: "$SKIP_INFERENCE_TESTS"
PYTHONPATH=. SKIP_INFERENCE_TESTS=$SKIP_INFERENCE_TESTS pytest -vv scripts/smoketest.py

#######################
# Test parallel vs single mode
#######################
if ! $SKIP_INFERENCE_TESTS; then
    start_container 9000 true
    await_server_ready 9000

    echo Running parallel mode test
    ./scripts/parallel-mode-test.sh localhost:8000 localhost:9000
fi

result=$?
exit $result
