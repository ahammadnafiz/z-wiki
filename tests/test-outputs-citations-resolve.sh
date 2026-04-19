#!/usr/bin/env bash
# Every [[wikilink]] inside wiki/outputs/*.md resolves to an existing
# page. Catches QUERY fabrication: spec says "never invent
# citations" and this test is the structural enforcement.
#
# Uses plain grep rather than rg — tests must work under `bash
# script.sh` invocation, which doesn't inherit shell functions.
set -u
cd "$(dirname "$0")/.."

OUT=wiki/outputs
[ -d "$OUT" ] || exit 0

slug_file=$(mktemp -t z-wiki-out-slugs-XXXXXX)
violations_file=$(mktemp -t z-wiki-out-violations-XXXXXX)
trap 'rm -f "$slug_file" "$violations_file"' EXIT

find wiki \
  \( -path wiki/.meta -o -path wiki/attachments -o -path wiki/canvases -o -path wiki/views -o -path wiki/indexes \) -prune -o \
  -type f -name '*.md' -print |
  while IFS= read -r f; do basename "$f" .md; done |
  sort -u > "$slug_file"

# For every output file, extract [[...]] tokens with grep -oE and
# validate each target against the slug list.
find "$OUT" -type f -name '*.md' -not -name '_index*.md' -print |
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
      echo "UNRESOLVED CITATION: $file [[${inner}]]" >> "$violations_file"
    fi
  done
done

if [ -s "$violations_file" ]; then
  cat "$violations_file"
  count=$(wc -l < "$violations_file" | tr -d ' ')
  echo ""
  echo "$count unresolved citation(s) in wiki/outputs/"
  echo "This is QUERY fabrication — an output cites a page that doesn't exist."
  echo "Delete the bad citation, or add a raw source and re-run /wiki-ingest."
  exit 1
fi
exit 0
