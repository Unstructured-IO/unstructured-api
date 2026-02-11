#!/usr/bin/env bash

# parallel-mode-test.sh
# Iterate a list of curl commands, and run each one against two instances of the api
# The smoke test will start one container with parallel mode and one without, and
# diff the two outputs to make sure parallel mode does not alter the response.
# Note the filepaths assume you ran this from the top level

# shellcheck disable=SC2317,SC2086  # SC2317: trap functions appear unreachable, SC2086: curl params require word splitting

base_url_1=$1
base_url_2=$2
MAX_RETRIES=3

curl_with_retry() {
    local curl_command=$1
    local output_file=$2

    for attempt in $(seq 1 $MAX_RETRIES); do
        $curl_command 2> /dev/null | jq -S 'del(..|.parent_id?)' > "$output_file"
        if [ -s "$output_file" ]; then
            return 0
        fi
        echo "  Attempt $attempt/$MAX_RETRIES failed, retrying in 5s..."
        sleep 5
    done

    echo "  All $MAX_RETRIES attempts failed!"
    $curl_command
    return 1
}

declare -a curl_params=(
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'strategy=fast'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'strategy=auto"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'strategy=hi_res'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'coordinates=true'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'encoding=utf-8'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'include_page_breaks=true'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'hi_res_model_name=yolox'"
)

for params in "${curl_params[@]}"
do
   curl_command="curl $base_url_1/general/v0/general $params"
   echo Testing: "$curl_command"

   # Run in single mode
   # Note(austin): Parallel mode screws up hierarchy! While we deal with that,
   # let's ignore parent_id fields in the results
   if ! curl_with_retry "$curl_command" output.json; then
       echo Command failed!
       exit 1
   fi
   original_length=$(jq 'length' output.json)

   # Run in parallel mode
   curl_command="curl $base_url_2/general/v0/general $params"
   if ! curl_with_retry "$curl_command" parallel_output.json; then
       echo Command failed!
       exit 1
   fi
   parallel_length=$(jq 'length' parallel_output.json)

   if ! [[ "$original_length" == "$parallel_length" ]]; then
       echo Parallel mode returned a different number of elements!
       echo Params: "$params"
       exit 1
   fi

   rm -f output.json parallel_output.json
   echo
done
