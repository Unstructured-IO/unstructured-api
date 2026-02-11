#!/usr/bin/env bash

# parallel-mode-test.sh
# Run each test case against two instances of the api (single mode vs parallel mode)
# and diff the outputs to make sure parallel mode does not alter the response.
# All test cases run concurrently for speed.
# Note the filepaths assume you ran this from the top level

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

set -e

base_url_1=$1
base_url_2=$2

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

declare -a curl_params=(
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'strategy=fast'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'strategy=auto"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'strategy=hi_res'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'coordinates=true'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'encoding=utf-8'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'include_page_breaks=true'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'hi_res_model_name=yolox'"
)

run_test_case() {
    local idx=$1
    local params=$2
    local single_output="$tmpdir/single_${idx}.json"
    local parallel_output="$tmpdir/parallel_${idx}.json"

    curl_command="curl $base_url_1/general/v0/general $params"
    echo "[$idx] Testing: $curl_command"

    # Run in single mode
    # Note(austin): Parallel mode screws up hierarchy! While we deal with that,
    # let's ignore parent_id fields in the results
    $curl_command 2> /dev/null | jq -S 'del(..|.parent_id?)' > "$single_output"

    # Stop if curl didn't work
    if [ ! -s "$single_output" ]; then
        echo "[$idx] Single mode command failed!"
        $curl_command
        return 1
    fi

    # Run in parallel mode
    curl_command="curl $base_url_2/general/v0/general $params"
    $curl_command 2> /dev/null | jq -S 'del(..|.parent_id?)' > "$parallel_output"

    # Stop if curl didn't work
    if [ ! -s "$parallel_output" ]; then
        echo "[$idx] Parallel mode command failed!"
        $curl_command
        return 1
    fi

    local original_length
    local parallel_length
    original_length=$(jq 'length' "$single_output")
    parallel_length=$(jq 'length' "$parallel_output")

    if [[ "$original_length" != "$parallel_length" ]]; then
        echo "[$idx] Parallel mode returned a different number of elements! ($original_length vs $parallel_length)"
        echo "[$idx] Params: $params"
        return 1
    fi

    echo "[$idx] PASSED ($original_length elements)"
}

# Launch all test cases concurrently
pids=()
for i in "${!curl_params[@]}"; do
    run_test_case "$i" "${curl_params[$i]}" &
    pids+=($!)
done

# Wait for all and collect failures
failed=0
for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
        echo "Test case $i failed!"
        failed=1
    fi
done

if [ "$failed" -ne 0 ]; then
    echo "Some parallel mode tests failed!"
    exit 1
fi

echo "All parallel mode tests passed!"
