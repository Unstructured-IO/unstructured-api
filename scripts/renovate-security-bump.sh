#!/usr/bin/env bash

set -euo pipefail

# Shared script for Renovate to bump version and update CHANGELOG
# Supports both __version__.py and pyproject.toml versioning styles
# Auto-detects changed dependencies from git diff

# Use current working directory as repo root (where Renovate executes the script)
REPO_ROOT="${REPO_ROOT:-$(pwd)}"
CHANGELOG_FILE="${CHANGELOG_FILE:-$REPO_ROOT/CHANGELOG.md}"

# VERSION_FILE can be:
# - Path to __version__.py (traditional Python)
# - Path to pyproject.toml (modern Python with uv/poetry)
# - "auto" or unset to auto-detect
VERSION_FILE="${VERSION_FILE:-auto}"

echo "=== Renovate Security Version Bump ==="

# Auto-detect versioning style
detect_version_style() {
  if [[ "$VERSION_FILE" == "auto" ]]; then
    # Check for pyproject.toml with version field first (modern style)
    if [[ -f "$REPO_ROOT/pyproject.toml" ]] && grep -qE "^version\s*=" "$REPO_ROOT/pyproject.toml"; then
      VERSION_FILE="$REPO_ROOT/pyproject.toml"
      VERSION_STYLE="pyproject"
      echo "Auto-detected: pyproject.toml versioning"
    # Check for common __version__.py locations
    elif [[ -f "$REPO_ROOT/unstructured/__version__.py" ]]; then
      VERSION_FILE="$REPO_ROOT/unstructured/__version__.py"
      VERSION_STYLE="python"
      echo "Auto-detected: __version__.py versioning"
    else
      echo "Error: Could not auto-detect version file. Set VERSION_FILE explicitly."
      exit 1
    fi
  elif [[ "$VERSION_FILE" == *.py ]]; then
    VERSION_STYLE="python"
    echo "Using Python __version__.py style: $VERSION_FILE"
  elif [[ "$VERSION_FILE" == *pyproject.toml ]]; then
    VERSION_STYLE="pyproject"
    echo "Using pyproject.toml style: $VERSION_FILE"
  else
    echo "Error: Unknown version file type: $VERSION_FILE"
    exit 1
  fi
}

# Read current version based on style
read_current_version() {
  if [[ "$VERSION_STYLE" == "python" ]]; then
    CURRENT_VERSION=$(grep -o -E "(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-dev[0-9]*)?" "$VERSION_FILE" | head -1)
  elif [[ "$VERSION_STYLE" == "pyproject" ]]; then
    # Extract version from pyproject.toml (detect quote style for portability)
    if grep -qE "^version\s*=\s*\"" "$VERSION_FILE"; then
      # Double quotes - match and discard trailing content (comments, etc)
      CURRENT_VERSION=$(grep -E "^version\s*=" "$VERSION_FILE" | head -1 | sed -E 's/version\s*=\s*"([^"]+)".*/\1/' | tr -d ' ')
    else
      # Single quotes (portable - avoid \x27 which breaks on BSD sed)
      CURRENT_VERSION=$(grep -E "^version\s*=" "$VERSION_FILE" | head -1 | sed -E "s/version\s*=\s*'([^']+)'.*/\1/" | tr -d ' ')
    fi
  fi
  echo "Current version: $CURRENT_VERSION"
}

# Calculate new release version
calculate_release_version() {
  if [[ "$CURRENT_VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)(-dev[0-9]*)?$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
    DEV_SUFFIX="${BASH_REMATCH[4]}"

    if [[ -n "$DEV_SUFFIX" ]]; then
      # Strip -dev suffix to release current version
      RELEASE_VERSION="$MAJOR.$MINOR.$PATCH"
      echo "Stripping dev suffix: $CURRENT_VERSION → $RELEASE_VERSION"
    else
      # Already a release version, bump to next patch
      NEW_PATCH=$((PATCH + 1))
      RELEASE_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
      echo "Bumping patch version: $CURRENT_VERSION → $RELEASE_VERSION"
    fi
  else
    echo "Error: Could not parse version: $CURRENT_VERSION"
    exit 1
  fi
}

# Update version in __version__.py
update_python_version() {
  echo "Updating $VERSION_FILE to version $RELEASE_VERSION"

  # Detect quote style used in the file
  if grep -q "__version__ = ['\"]" "$VERSION_FILE"; then
    if grep -q "__version__ = \"" "$VERSION_FILE"; then
      # Double quotes
      sed -i.bak -E "s/__version__ = \"[^\"]+\"/__version__ = \"$RELEASE_VERSION\"/" "$VERSION_FILE"
    else
      # Single quotes
      sed -i.bak -E "s/__version__ = '[^']+'/__version__ = '$RELEASE_VERSION'/" "$VERSION_FILE"
    fi
  else
    echo "Error: Could not detect quote style in $VERSION_FILE"
    exit 1
  fi

  # Verify the update succeeded
  if ! grep -q "__version__ = ['\"]${RELEASE_VERSION}['\"]" "$VERSION_FILE"; then
    echo "Error: Failed to update version in $VERSION_FILE"
    exit 1
  fi

  rm -f "$VERSION_FILE.bak"
}

# Update version in pyproject.toml
update_pyproject_version() {
  echo "Updating $VERSION_FILE to version $RELEASE_VERSION"

  # Detect quote style (single or double quotes)
  if grep -qE "^version\s*=\s*\"" "$VERSION_FILE"; then
    # Double quotes
    sed -i.bak -E "s/^(version\s*=\s*)\"[^\"]+\"/\1\"$RELEASE_VERSION\"/" "$VERSION_FILE"
  else
    # Single quotes
    sed -i.bak -E "s/^(version\s*=\s*)'[^']+'/\1'$RELEASE_VERSION'/" "$VERSION_FILE"
  fi

  # Verify the update succeeded
  if ! grep -qE "^version\s*=\s*['\"]${RELEASE_VERSION}['\"]" "$VERSION_FILE"; then
    echo "Error: Failed to update version in $VERSION_FILE"
    exit 1
  fi

  rm -f "$VERSION_FILE.bak"
}

# Detect changed packages from git diff
detect_changed_packages() {
  echo "Detecting changed dependencies..."

  # Package name regex per PEP 508: starts with letter/digit, can contain letters, digits, dots, underscores, hyphens
  local pkg_pattern='^[-+][a-zA-Z0-9][a-zA-Z0-9._-]*=='

  # Try requirements/*.txt files first (pip-compile output format)
  CHANGED_PACKAGES=$(git diff --cached requirements/*.txt 2>/dev/null | grep -E "$pkg_pattern" | sed 's/^[+-]//' | sort -u | head -20 || true)

  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff requirements/*.txt 2>/dev/null | grep -E "$pkg_pattern" | sed 's/^[+-]//' | sort -u | head -20 || true)
  fi

  # Try requirements/*.in files (unpinned requirements)
  # Strip comments, extras [.*], version specifiers; exclude URLs and flags
  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff --cached requirements/*.in 2>/dev/null | grep -E '^[-+][a-zA-Z0-9][a-zA-Z0-9._-]*' | grep -v '^[-+]#' | grep -v '^[-+]-' | grep -v '://' | sed 's/^[+-]//' | sed -E 's/#.*//; s/\[.*//; s/[<>=~].*//' | sed 's/[[:space:]]*$//' | sort -u | head -20 || true)
  fi

  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff requirements/*.in 2>/dev/null | grep -E '^[-+][a-zA-Z0-9][a-zA-Z0-9._-]*' | grep -v '^[-+]#' | grep -v '^[-+]-' | grep -v '://' | sed 's/^[+-]//' | sed -E 's/#.*//; s/\[.*//; s/[<>=~].*//' | sed 's/[[:space:]]*$//' | sort -u | head -20 || true)
  fi

  # Try uv.lock if no requirements changes found
  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff --cached uv.lock 2>/dev/null | grep -E '^[-+]name\s*=' | sed -E 's/^[-+]name\s*=\s*"([^"]+)"/\1/' | sort -u | head -20 || true)
  fi

  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff uv.lock 2>/dev/null | grep -E '^[-+]name\s*=' | sed -E 's/^[-+]name\s*=\s*"([^"]+)"/\1/' | sort -u | head -20 || true)
  fi

  # Try pyproject.toml dependencies section
  # Match version specifiers (<>=~^!), extras [, quotes ", commas, or end of line for unversioned
  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff --cached pyproject.toml 2>/dev/null | grep -E '^[-+]\s*"?[a-zA-Z0-9][a-zA-Z0-9._-]*([<>=~^!\[",]|$)' | sed -E 's/^[-+]\s*"?([a-zA-Z0-9][a-zA-Z0-9._-]*).*/\1/' | sort -u | head -20 || true)
  fi

  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff pyproject.toml 2>/dev/null | grep -E '^[-+]\s*"?[a-zA-Z0-9][a-zA-Z0-9._-]*([<>=~^!\[",]|$)' | sed -E 's/^[-+]\s*"?([a-zA-Z0-9][a-zA-Z0-9._-]*).*/\1/' | sort -u | head -20 || true)
  fi

  # Build changelog entry
  if [ -n "$CHANGED_PACKAGES" ]; then
    PACKAGE_COUNT=$(echo "$CHANGED_PACKAGES" | wc -l | tr -d ' ')
    echo "Found $PACKAGE_COUNT changed package(s):"
    echo "$CHANGED_PACKAGES" | head -5 | sed 's/^/  - /'
    if [ "$PACKAGE_COUNT" -gt 5 ]; then
      echo "  ... and $((PACKAGE_COUNT - 5)) more"
    fi

    # Build specific changelog entry with package names
    if [ "$PACKAGE_COUNT" -eq 1 ]; then
      PACKAGE_NAME=$(echo "$CHANGED_PACKAGES" | head -1 | cut -d'=' -f1)
      CHANGELOG_ENTRY="- **Security update**: Updated \`${PACKAGE_NAME}\` to address security vulnerability"
    elif [ "$PACKAGE_COUNT" -le 3 ]; then
      PACKAGE_NAMES=$(echo "$CHANGED_PACKAGES" | cut -d'=' -f1 | paste -sd, - | sed 's/,/, /g' | sed 's/\([^,]*\)/`\1`/g')
      CHANGELOG_ENTRY="- **Security update**: Updated ${PACKAGE_NAMES} to address security vulnerabilities"
    else
      CHANGELOG_ENTRY="- **Security update**: Updated ${PACKAGE_COUNT} dependencies to address security vulnerabilities"
    fi
  else
    echo "Could not auto-detect packages, using generic entry"
    CHANGELOG_ENTRY="- **Security update**: Bumped dependencies to address security vulnerabilities"
  fi

  echo "Changelog entry: $CHANGELOG_ENTRY"
}

# Detect CHANGELOG format from existing entries
detect_changelog_format() {
  # Check if headers use brackets: ## [1.2.3] vs ## 1.2.3
  if grep -q -m 1 -E '^## \[[0-9]+\.[0-9]+\.[0-9]+' "$CHANGELOG_FILE" 2>/dev/null; then
    CHANGELOG_USE_BRACKETS=true
    echo "Detected CHANGELOG format: bracketed headers (## [version])"
  else
    CHANGELOG_USE_BRACKETS=false
    echo "Detected CHANGELOG format: plain headers (## version)"
  fi

  # Check if CHANGELOG uses subsections (### Fixes) or direct bullets
  if grep -q -m 1 '^### ' "$CHANGELOG_FILE" 2>/dev/null; then
    CHANGELOG_USE_SUBSECTIONS=true
    echo "Detected CHANGELOG format: uses subsections (### Fixes)"
  else
    CHANGELOG_USE_SUBSECTIONS=false
    echo "Detected CHANGELOG format: direct bullet points"
  fi
}

# Update CHANGELOG.md
update_changelog() {
  echo "Updating CHANGELOG..."

  # Check if CHANGELOG exists
  if [[ ! -f "$CHANGELOG_FILE" ]]; then
    echo "Warning: CHANGELOG.md not found at $CHANGELOG_FILE, skipping changelog update"
    return 0
  fi

  # Detect the format
  detect_changelog_format

  # Only look for -dev version to rename if CURRENT_VERSION had -dev suffix
  if [[ -n "${DEV_SUFFIX:-}" ]]; then
    # Look for -dev version header in CHANGELOG that matches our version exactly (not substring)
    # Escape dots for regex, handle brackets if used
    ESCAPED_VERSION="${CURRENT_VERSION//./\\.}"
    if [ "$CHANGELOG_USE_BRACKETS" = true ]; then
      DEV_VERSION_HEADER=$(grep -m 1 -E "^## \[${ESCAPED_VERSION}\]" "$CHANGELOG_FILE" || true)
    else
      DEV_VERSION_HEADER=$(grep -m 1 -E "^## ${ESCAPED_VERSION}(\s*$)" "$CHANGELOG_FILE" || true)
    fi

    if [[ -n "$DEV_VERSION_HEADER" ]]; then
      echo "Found dev version in CHANGELOG: $DEV_VERSION_HEADER"

      # Extract the -dev version number from header
      DEV_VERSION=$(echo "$DEV_VERSION_HEADER" | grep -o -E "[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]*")

      echo "Renaming CHANGELOG header: $DEV_VERSION → $RELEASE_VERSION"

      awk -v dev_version="$DEV_VERSION" \
        -v release_version="$RELEASE_VERSION" \
        -v security_entry="$CHANGELOG_ENTRY" \
        -v use_brackets="$CHANGELOG_USE_BRACKETS" \
        -v use_subsections="$CHANGELOG_USE_SUBSECTIONS" '
        BEGIN {
          in_target_version = 0
          found_fixes = 0
          added_entry = 0
        }

        /^## / {
          # Match the dev version header (with or without brackets)
          dev_header = use_brackets == "true" ? "## [" dev_version "]" : "## " dev_version
          release_header = use_brackets == "true" ? "## [" release_version "]" : "## " release_version

          if (index($0, dev_header) == 1) {
            print release_header
            in_target_version = 1
            next
          } else {
            if (in_target_version && !found_fixes && !added_entry) {
              if (use_subsections == "true") {
                print ""
                print "### Fixes"
              }
              print security_entry
              if (use_subsections == "true") {
                print ""
              }
              added_entry = 1
            }
            in_target_version = 0
            found_fixes = 0
          }
        }

        /^### Fixes/ && in_target_version && use_subsections == "true" {
          print
          print security_entry
          found_fixes = 1
          added_entry = 1
          next
        }

        { print }

        END {
          if (in_target_version && !found_fixes && !added_entry) {
            if (use_subsections == "true") {
              print ""
              print "### Fixes"
            }
            print security_entry
          }
        }
      ' "$CHANGELOG_FILE" >"$CHANGELOG_FILE.tmp"

      mv "$CHANGELOG_FILE.tmp" "$CHANGELOG_FILE"
    else
      echo "Warning: Current version has -dev suffix but no matching dev header in CHANGELOG"
      create_new_changelog_entry
    fi
  else
    # Current version was already a release, so we bumped to next patch
    create_new_changelog_entry
  fi
}

create_new_changelog_entry() {
  echo "Creating new CHANGELOG entry for $RELEASE_VERSION"

  local tmp_file
  tmp_file=$(mktemp)

  # Format header based on detected style
  local header
  if [ "$CHANGELOG_USE_BRACKETS" = true ]; then
    header="## [$RELEASE_VERSION]"
  else
    header="## $RELEASE_VERSION"
  fi

  # Build entry based on subsection style
  if [ "$CHANGELOG_USE_SUBSECTIONS" = true ]; then
    cat >"$tmp_file" <<EOF
$header

### Fixes
$CHANGELOG_ENTRY

EOF
  else
    cat >"$tmp_file" <<EOF
$header

$CHANGELOG_ENTRY

EOF
  fi

  cat "$tmp_file" "$CHANGELOG_FILE" >"$CHANGELOG_FILE.tmp"
  mv "$CHANGELOG_FILE.tmp" "$CHANGELOG_FILE"
  rm -f "$tmp_file"
}

# Main execution
detect_version_style
read_current_version
calculate_release_version

if [[ "$VERSION_STYLE" == "python" ]]; then
  update_python_version
elif [[ "$VERSION_STYLE" == "pyproject" ]]; then
  update_pyproject_version
fi

detect_changed_packages
update_changelog

echo ""
echo "✓ Successfully updated version to $RELEASE_VERSION"
echo "✓ Updated CHANGELOG with security fix entry"
echo ""
echo "Modified files:"
echo "  - $VERSION_FILE"
if [[ -f "$CHANGELOG_FILE" ]]; then
  echo "  - $CHANGELOG_FILE"
fi
