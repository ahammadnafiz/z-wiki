#!/usr/bin/env bash
# No two non-generated wiki pages share a filename. Obsidian wikilink
# resolution depends on globally unique filenames.
# _index*.md is generated per-directory and excluded from this check.
set -u
cd "$(dirname "$0")/.."

dupes=$(
  find wiki \
    \( -path wiki/.meta -o -path wiki/attachments \) -prune -o \
    -type f -name '*.md' -not -name '_index*.md' -print |
    while IFS= read -r f; do basename "$f"; done |
    sort |
    uniq -d
)

if [ -n "$dupes" ]; then
  echo "duplicate slug(s):"
  echo "$dupes" | sed 's/^/  /'
  echo
  echo "affected files:"
  while IFS= read -r slug; do
    [ -z "$slug" ] && continue
    find wiki -type f -name "$slug" | sed 's/^/  /'
  done <<< "$dupes"
  exit 1
fi
exit 0
