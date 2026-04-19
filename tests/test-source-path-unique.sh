#!/usr/bin/env bash
# No two wiki/sources/*.md share the same source_path: value. A
# duplicate source_path means the same raw file was ingested twice
# under different slugs — bug.
set -u
cd "$(dirname "$0")/.."

dupes=$(
  rg -H -oN '^source_path:\s*"?([^"]+)"?\s*$' -r '$1' wiki/sources \
    --no-messages 2>/dev/null |
    awk -F: '{path=$1; $1=""; sub(/^:/,""); print $0 "\t" path}' |
    awk -F'\t' 'NF==2 {print $1}' |
    sort |
    uniq -d
)

if [ -n "$dupes" ]; then
  echo "duplicate source_path value(s):"
  echo "$dupes" | sed 's/^/  /'
  exit 1
fi
exit 0
