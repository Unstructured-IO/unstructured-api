#!/bin/bash

# parallel-mode-test.sh
# Iterate a list of curl commands, and run each one with parallel mode enabled/disabled.
# Diff the two outputs to make sure parallel mode does not alter the response.
# This is run by docker-smoke-test.sh after the container starts up, but
# you can also use it against dev/prod by passing an arg:
# e.g. ./scripts/parallel-mode-test.sh prod|dev
# Note the filepaths assume you ran this from the top level

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

if [[ $1 == "prod" ]]; then
    base_url="https://api.unstructured.io"
elif [[ $1 == "dev" ]]; then
    base_url="https://dev.api.unstructured.io"
else
    base_url="http://localhost:8000"
fi

declare -a curl_params=(
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'strategy=fast'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'strategy=auto"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'strategy=hi_res'"
    "-F files=@sample-docs/layout-parser-paper.pdf -F 'coordinates=true' -F 'strategy=fast'"
)

trap "rm -f output.json parallel_output.json" EXIT

for params in "${curl_params[@]}"
do
   curl_command="curl $base_url/general/v0/general $params"
   echo Testing: "$curl_command"

   # Run in single mode
   $curl_command 2> /dev/null | jq -S > output.json

   # Stop if curl didn't work
   if [ ! -s output.json ]; then
       echo Command failed!
       $curl_command
       exit 1
   fi

   # Run in parallel mode
   curl_command="$curl_command -F use_parallel_mode=true"
   $curl_command 2> /dev/null | jq -S > parallel_output.json

   if ! diff -u output.json parallel_output.json ; then
       echo Parallel mode received a different output!
       echo Params: "$params"
       exit 1
   fi

   echo
done


