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
}

await_server_ready() {
    url=localhost:8000/healthcheck

    for i in {1..5}; do
        echo Waiting for response from "$url"...
        curl $url 2> /dev/null
        if [[ $? = 0 ]]; then
            echo
            return
        fi

        sleep 5
    done

    echo Server did not respond!
    exit 1
}

stop_container() {
    echo Stopping container "$container_name"
    docker stop "$container_name"
}

start_container

# Regardless of test result, stop the container
trap stop_container EXIT

await_server_ready

echo Running tests
PYTHONPATH=. pytest scripts/smoketest.py

result=$?
exit $result
