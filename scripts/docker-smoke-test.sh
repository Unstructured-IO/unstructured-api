#!/usr/bin/env bash


# docker-smoke-test.sh
# Start the containerized api and run some end-to-end tests against it
# There will be some overlap with just running a TestClient in the unit tests
# Is there a good way to reuse code here?
# Also note this can evolve into a generalized pipeline smoke test

# shellcheck disable=SC2317,SC2329  # Shellcheck complains that trap functions are unreachable/unused...

set -e

CONTAINER_NAME_PREFIX=unstructured-api-smoke-test
CONTAINER_NAME_PARALLEL=unstructured-api-smoke-test-parallel
PIPELINE_FAMILY=${PIPELINE_FAMILY:-"general"}
DOCKER_IMAGE="${DOCKER_IMAGE:-pipeline-family-${PIPELINE_FAMILY}-dev:latest}"
SKIP_INFERENCE_TESTS="${SKIP_INFERENCE_TESTS:-false}"
NUM_WORKERS="${NUM_WORKERS:-4}"
BASE_PORT=8000

start_container() {
    local port=$1
    local name=$2
    local use_parallel_mode=${3:-false}

    echo Starting container "$name" on port "$port"
    docker run --platform "$DOCKER_PLATFORM" \
           -p "$port":"$port" \
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
    local port=$1
    local url=localhost:$port/healthcheck

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

stop_all_containers() {
    for i in $(seq 0 $((NUM_WORKERS-1))); do
        local name="${CONTAINER_NAME_PREFIX}-${i}"
        echo Stopping container "$name"
        docker stop "$name" 2> /dev/null || true
    done

    echo Stopping container "$CONTAINER_NAME_PARALLEL"
    docker stop "$CONTAINER_NAME_PARALLEL" 2> /dev/null || true
}

# Always clean up all containers
trap stop_all_containers EXIT

#######################
# Start worker containers
#######################
for i in $(seq 0 $((NUM_WORKERS-1))); do
    port=$((BASE_PORT + i))
    start_container "$port" "${CONTAINER_NAME_PREFIX}-${i}" "false"
done

for i in $(seq 0 $((NUM_WORKERS-1))); do
    port=$((BASE_PORT + i))
    await_server_ready "$port"
done

#######################
# Smoke Tests
#######################
echo "Running smoke tests with SKIP_INFERENCE_TESTS: $SKIP_INFERENCE_TESTS, NUM_WORKERS: $NUM_WORKERS"
PYTHONPATH=. SKIP_INFERENCE_TESTS=$SKIP_INFERENCE_TESTS SMOKE_TEST_BASE_PORT=$BASE_PORT \
    uv run pytest -n "$NUM_WORKERS" -vv scripts/smoketest.py

#######################
# Test parallel vs single mode
#######################
if ! $SKIP_INFERENCE_TESTS; then
    # Stop all smoke test containers to free memory and avoid stale state
    for i in $(seq 0 $((NUM_WORKERS-1))); do
        docker stop "${CONTAINER_NAME_PREFIX}-${i}" 2> /dev/null || true
    done

    # Start fresh containers for the parallel-mode comparison test
    single_port=$BASE_PORT
    parallel_port=$((BASE_PORT + 1))
    start_container "$single_port" "${CONTAINER_NAME_PREFIX}-0" "false"
    start_container "$parallel_port" "$CONTAINER_NAME_PARALLEL" "true"
    await_server_ready "$single_port"
    await_server_ready "$parallel_port"

    echo Running parallel mode test
    ./scripts/parallel-mode-test.sh "localhost:$single_port" "localhost:$parallel_port"
fi

result=$?
exit $result
