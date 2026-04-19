#!/usr/bin/env bash
# Filenames under wiki/ are lowercase kebab-case ASCII.
# Allowed exceptions: _index*.md (generated), README.md.
set -u
cd "$(dirname "$0")/.."

violations=$(
  find wiki \
    \( -path wiki/.meta -o -path wiki/attachments \) -prune -o \
    -type f -name '*.md' \
    -not -name '_index*.md' \
    -not -name 'README.md' \
    -print |
    while IFS= read -r f; do
      base=$(basename "$f")
      if ! echo "$base" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*\.md$'; then
        echo "$f"
      fi
    done
)

if [ -n "$violations" ]; then
  echo "non-kebab-case filename(s):"
  echo "$violations" | sed 's/^/  /'
  exit 1
fi
exit 0
