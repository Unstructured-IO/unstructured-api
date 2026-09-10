#!/usr/bin/env bash

set -euo pipefail

base_url_1=$1
base_url_2=$2
results_dir=$(mktemp -d)
trap 'rm -rf "$results_dir"' EXIT

request_elements() {
    local base_url=$1
    local output_file=$2
    shift 2

    curl --fail --silent --show-error --retry 2 --max-time 300 \
        "$base_url/general/v0/general" \
        -F files=@sample-docs/layout-parser-paper.pdf \
        "$@" > "$output_file"
    jq -e 'type == "array" and length > 0' "$output_file" > /dev/null
}

for option in strategy=fast strategy=auto strategy=hi_res coordinates=true encoding=utf-8 include_page_breaks=true hi_res_model_name=yolox; do
    # Exercise forwarding options without repeating inference for each one.
    case "$option" in
        strategy=*) form_args=(-F "$option") ;;
        hi_res_model_name=*) form_args=(-F strategy=hi_res -F "$option") ;;
        *) form_args=(-F strategy=fast -F "$option") ;;
    esac

    echo "Testing: $option"
    request_elements "$base_url_1" "$results_dir/single.json" "${form_args[@]}"
    request_elements "$base_url_2" "$results_dir/parallel.json" "${form_args[@]}"

    original_length=$(jq 'length' "$results_dir/single.json")
    parallel_length=$(jq 'length' "$results_dir/parallel.json")
    if [[ "$original_length" != "$parallel_length" ]]; then
        echo "Parallel mode returned a different number of elements for $option"
        exit 1
    fi
done
