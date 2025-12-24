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
    if [[ -f "$REPO_ROOT/pyproject.toml" ]] && grep -q "^version\s*=" "$REPO_ROOT/pyproject.toml"; then
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
    CURRENT_VERSION=$(grep -o -E "(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-dev[0-9]+)?" "$VERSION_FILE")
  elif [[ "$VERSION_STYLE" == "pyproject" ]]; then
    # Extract version from pyproject.toml (handles both quoted styles)
    CURRENT_VERSION=$(grep -E "^version\s*=" "$VERSION_FILE" | head -1 | sed -E 's/version\s*=\s*["\x27]?([^"\x27]+)["\x27]?/\1/' | tr -d ' ')
  fi
  echo "Current version: $CURRENT_VERSION"
}

# Calculate new release version
calculate_release_version() {
  if [[ "$CURRENT_VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)(-dev.*)?$ ]]; then
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
    sed -i.bak -E "s/^(version\s*=\s*)'[^']+'$/\1'$RELEASE_VERSION'/" "$VERSION_FILE"
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

  # Try requirements files first
  CHANGED_PACKAGES=$(git diff --cached requirements/*.txt 2>/dev/null | grep -E "^[-+][a-zA-Z0-9_-]+==" | sed 's/^[+-]//' | sort -u | head -20 || true)

  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff requirements/*.txt 2>/dev/null | grep -E "^[-+][a-zA-Z0-9_-]+==" | sed 's/^[+-]//' | sort -u | head -20 || true)
  fi

  # Try uv.lock if no requirements changes found
  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff --cached uv.lock 2>/dev/null | grep -E "^[-+]name\s*=" | sed -E 's/^[-+]name\s*=\s*"([^"]+)"/\1/' | sort -u | head -20 || true)
  fi

  if [ -z "$CHANGED_PACKAGES" ]; then
    CHANGED_PACKAGES=$(git diff uv.lock 2>/dev/null | grep -E "^[-+]name\s*=" | sed -E 's/^[-+]name\s*=\s*"([^"]+)"/\1/' | sort -u | head -20 || true)
  fi

  # Build changelog entry
  if [ -n "$CHANGED_PACKAGES" ]; then
    PACKAGE_COUNT=$(echo "$CHANGED_PACKAGES" | wc -l | tr -d ' ')
    echo "Found $PACKAGE_COUNT changed package(s)"
  else
    echo "Could not auto-detect packages, using generic entry"
  fi

  CHANGELOG_ENTRY="- **Security update**: Bumped dependencies to address security vulnerabilities"
  echo "Changelog entry: $CHANGELOG_ENTRY"
}

# Update CHANGELOG.md
update_changelog() {
  echo "Updating CHANGELOG..."

  # Check if CHANGELOG exists
  if [[ ! -f "$CHANGELOG_FILE" ]]; then
    echo "Warning: CHANGELOG.md not found at $CHANGELOG_FILE, skipping changelog update"
    return 0
  fi

  # Only look for -dev version to rename if CURRENT_VERSION had -dev suffix
  if [[ -n "${DEV_SUFFIX:-}" ]]; then
    # Look for -dev version header in CHANGELOG that matches our version
    DEV_VERSION_HEADER=$(grep -m 1 -F "## $CURRENT_VERSION" "$CHANGELOG_FILE" || true)

    if [[ -n "$DEV_VERSION_HEADER" ]]; then
      echo "Found dev version in CHANGELOG: $DEV_VERSION_HEADER"

      # Extract the -dev version number from header
      DEV_VERSION=$(echo "$DEV_VERSION_HEADER" | grep -o -E "[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]*")

      echo "Renaming CHANGELOG header: $DEV_VERSION → $RELEASE_VERSION"

      awk -v dev_version="$DEV_VERSION" \
        -v release_version="$RELEASE_VERSION" \
        -v security_entry="$CHANGELOG_ENTRY" '
        BEGIN {
          in_target_version = 0
          found_fixes = 0
          added_entry = 0
        }

        /^## / {
          if ($0 ~ "^## " dev_version) {
            print "## " release_version
            in_target_version = 1
            next
          } else {
            if (in_target_version && !found_fixes && !added_entry) {
              print ""
              print "### Fixes"
              print security_entry
              print ""
              added_entry = 1
            }
            in_target_version = 0
            found_fixes = 0
          }
        }

        /^### Fixes/ && in_target_version {
          print
          print security_entry
          found_fixes = 1
          added_entry = 1
          next
        }

        { print }

        END {
          if (in_target_version && !found_fixes && !added_entry) {
            print ""
            print "### Fixes"
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

  cat >/tmp/new_changelog_section.tmp <<EOF
## $RELEASE_VERSION

### Fixes
$CHANGELOG_ENTRY

EOF

  cat /tmp/new_changelog_section.tmp "$CHANGELOG_FILE" >"$CHANGELOG_FILE.tmp"
  mv "$CHANGELOG_FILE.tmp" "$CHANGELOG_FILE"
  rm -f /tmp/new_changelog_section.tmp
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
