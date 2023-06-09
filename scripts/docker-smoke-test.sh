#!/bin/bash

# docker-smoke-test.sh
# Start the containerized api and run some end-to-end tests against it
# There will be some overlap with just running a TestClient in the unit tests
# Is there a good way to reuse code here?
# Also note this can evolve into a generalized pipeline smoke test

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

CONTAINER_NAME=unstructured-api-smoke-test
PIPELINE_FAMILY=${PIPELINE_FAMILY:-"general"}
DOCKER_IMAGE="${DOCKER_IMAGE:-pipeline-family-${PIPELINE_FAMILY}-dev:latest}"
API_PORT=8000
SKIP_INFERENCE_TESTS="${SKIP_INFERENCE_TESTS:-false}"

start_container() {
    echo Starting container "$CONTAINER_NAME"
    use_parallel_mode=$1

    docker run -p $API_PORT:$API_PORT \
           -d \
           --rm \
           --name "$CONTAINER_NAME" \
           --env "UNSTRUCTURED_PARALLEL_MODE_ENABLED=$use_parallel_mode" \
           --env "UNSTRUCTURED_PARALLEL_MODE_URL=http://localhost:$API_PORT/general/v0/general" \
           "$DOCKER_IMAGE" \
           --port $API_PORT --host 0.0.0.0
}

await_server_ready() {
    url=localhost:$API_PORT/healthcheck

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
    # Note (austin) - could be useful to dump the logs on an error
    # docker logs $CONTAINER_NAME 2> docker_logs.txt
    docker stop "$CONTAINER_NAME"
}

# Always clean up the container
trap stop_container EXIT

start_container "false"
await_server_ready

#######################
# Smoke Tests
#######################
echo Running smoke tests
PYTHONPATH=. SKIP_INFERENCE_TESTS=$SKIP_INFERENCE_TESTS pytest scripts/smoketest.py

#######################
# Test parallel vs single mode
#######################
echo Running parallel mode test

curl http://localhost:$API_PORT/general/v0/general --form 'files=@sample-docs/layout-parser-paper.pdf' --form 'coordinate=true' --form 'strategy=fast' | jq -S > single-mode.json

stop_container
start_container "true"
await_server_ready

curl http://localhost:$API_PORT/general/v0/general --form 'files=@sample-docs/layout-parser-paper.pdf' --form 'coordinates=true'--form 'strategy=fast' | jq -S > parallel-mode.json

if ! diff -u single-mode.json parallel-mode.json ; then
    echo Parallel mode received a different output!
    exit 1
fi

rm single-mode.json parallel-mode.json

result=$?
exit $result
