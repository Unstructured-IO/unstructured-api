#!/usr/bin/env bash

# parallel-mode-test.sh
# Iterate a list of curl commands, and run each one against two instances of the api
# The smoke test will start one container with parallel mode and one without, and
# diff the two outputs to make sure parallel mode does not alter the response.
# Note the filepaths assume you ran this from the top level

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

base_url_1=$1
base_url_2=$2

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
   $curl_command 2> /dev/null | jq -S 'del(..|.parent_id?)' > output.json
   original_length=$(jq 'length' output.json)

   # Stop if curl didn't work
   if [ ! -s output.json ]; then
       echo Command failed!
       $curl_command
       exit 1
   fi

   # Run in parallel mode
   curl_command="curl $base_url_2/general/v0/general $params"
   $curl_command 2> /dev/null | jq -S 'del(..|.parent_id?)' > parallel_output.json
   parallel_length=$(jq 'length' parallel_output.json)

   # Stop if curl didn't work
   if [ ! -s parallel_output.json ]; then
       echo Command failed!
       $curl_command
       exit 1
   fi

   if ! [[ "$original_length" == "$parallel_length" ]]; then
       echo Parallel mode returned a different number of elements!
       echo Params: "$params"
       exit 1
   fi

   rm -f output.json parallel_output.json
   echo
done


