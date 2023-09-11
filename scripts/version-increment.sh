#!/bin/bash
function usage {
    echo "Usage: $(basename "$0") CHANGELOG_MESSAGE" 2>&1
    echo 'Add the given message to the changelog and cut a release'
    echo "Example: $(basename "$0") \"Bump unstructured to x.y.z\""
}

# Found at https://www.henryschmale.org/2019/04/30/incr-semver.html
# $1 - semver string
# $2 - level to incr {dev,release,minor,major} - release by default
function incr_semver() {
    IFS='.' read -ra ver <<< "$1"
    [[ "${#ver[@]}" -ne 3 ]] && echo "Invalid semver string" && return 1
    [[ "$#" -eq 1 ]] && level='release' || level=$2

    release=${ver[2]}
    minor=${ver[1]}
    major=${ver[0]}

    case $level in
        # Drop the dev tag
        dev)
            release=$(echo "$release" | awk -F '-' '{print $1}')
        ;;
        release)
            release=$((release+1))
        ;;
        minor)
            release=0
            minor=$((minor+1))
        ;;
        major)
            release=0
            minor=0
            major=$((major+1))
        ;;
        *)
            echo "Invalid level passed"
            return 2
    esac
    echo "$major.$minor.$release"
}


if [[ -z "$1" ]]; then
    usage
    exit 0
fi

changelog_text="* $1"
current_version=$(head -1 CHANGELOG.md | awk -F' ' '{print $2}')

# If dev version, add to current change list and cut the release
if [[ $current_version == *"dev"* ]]; then
    new_version=$(incr_semver "$current_version" dev)

    # Replace the version (drop the dev tag)
    sed -i 's/'"$current_version"'/'"$new_version"'/' CHANGELOG.md

    # Find the first bullet, add the new change above it
    sed -i '0,/^*/{s/\(^*.*\)/'"$changelog_text"'\n\1/}' CHANGELOG.md

# If not dev version, create a new release
else
    new_version=$(incr_semver "$current_version" release)

    cat <<EOF | cat - CHANGELOG.md > CHANGELOG.tmp
## $new_version

$changelog_text

EOF

  mv CHANGELOG.{tmp,md}

fi
