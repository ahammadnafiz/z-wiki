#!/usr/bin/env bash
# Every [[target]] in a wiki page body resolves to an existing page.
# Uses plain grep (not rg) because tests run under `bash script.sh`,
# which does not inherit Claude Code's interactive shell functions.
set -u
cd "$(dirname "$0")/.."

slug_file=$(mktemp -t z-wiki-slugs-XXXXXX)
violations_file=$(mktemp -t z-wiki-violations-XXXXXX)
trap 'rm -f "$slug_file" "$violations_file"' EXIT

find wiki \
  \( -path wiki/.meta -o -path wiki/attachments -o -path wiki/canvases -o -path wiki/views -o -path wiki/indexes \) -prune -o \
  -type f -name '*.md' -print |
  while IFS= read -r f; do basename "$f" .md; done |
  sort -u > "$slug_file"

find wiki \
  \( -path wiki/.meta -o -path wiki/attachments -o -path wiki/canvases -o -path wiki/views -o -path wiki/indexes \) -prune -o \
  -type f -name '*.md' -print |
while IFS= read -r file; do
  grep -oE '\[\[[^]]+\]\]' "$file" 2>/dev/null |
  while IFS= read -r link; do
    inner=${link#\[\[}
    inner=${inner%\]\]}
    core=${inner%%#*}
    core=${core%%|*}
    core=$(echo "$core" | awk '{$1=$1; print}')
    [ -z "$core" ] && continue
    if ! grep -qxF "$core" "$slug_file"; then
      echo "UNRESOLVED: $file [[${inner}]]" >> "$violations_file"
    fi
  done
done

if [ -s "$violations_file" ]; then
  cat "$violations_file"
  count=$(wc -l < "$violations_file" | tr -d ' ')
  echo ""
  echo "$count unresolved wikilink(s)"
  exit 1
fi
exit 0
