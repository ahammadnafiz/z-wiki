#!/usr/bin/env bash
# Every wikilink target and canvas file-ref in wiki/canvases/*.canvas and
# wiki/views/*.base must also exist as a real .md page in the vault.
#
# CLAUDE.md:50-58 declares canvases/bases as ornamental: "any knowledge in
# canvas must also exist in markdown". review.md §63-67 (P3) asks for a
# mechanical check so a future Claude (or user) can't quietly promote a
# .base/.canvas to the sole listing of some category.
#
# Currently zero .canvas / .base files exist, so this test is vacuously
# green; it activates the moment ornamental artifacts are added.
set -u
cd "$(dirname "$0")/.."

slug_file=$(mktemp -t z-wiki-slugs-XXXXXX)
path_file=$(mktemp -t z-wiki-mdpaths-XXXXXX)
violations_file=$(mktemp -t z-wiki-canvas-violations-XXXXXX)
trap 'rm -f "$slug_file" "$path_file" "$violations_file"' EXIT

# Slug set = every .md basename outside derived/ornamental dirs.
find wiki \
  \( -path wiki/.meta -o -path wiki/attachments -o -path wiki/canvases -o -path wiki/views -o -path wiki/indexes \) -prune -o \
  -type f -name '*.md' -print |
  while IFS= read -r f; do basename "$f" .md; done |
  sort -u > "$slug_file"

# Canonical paths (relative to wiki/) for "file": "..." JSON refs in .canvas.
find wiki \
  \( -path wiki/.meta -o -path wiki/attachments -o -path wiki/canvases -o -path wiki/views -o -path wiki/indexes \) -prune -o \
  -type f -name '*.md' -print |
  sed 's|^wiki/||' |
  sort -u > "$path_file"

check_wikilinks() {
  local file=$1
  grep -oE '\[\[[^]]+\]\]' "$file" 2>/dev/null |
    while IFS= read -r link; do
      inner=${link#\[\[}
      inner=${inner%\]\]}
      core=${inner%%#*}
      core=${core%%|*}
      core=$(echo "$core" | awk '{$1=$1; print}')
      [ -z "$core" ] && continue
      if ! grep -qxF "$core" "$slug_file"; then
        echo "UNRESOLVED wikilink: $file [[${inner}]]" >> "$violations_file"
      fi
    done
}

check_canvas_file_refs() {
  # Canvas is JSON; file-ref nodes look like {"type":"file","file":"path.md"}.
  # Grep the "file":"..." pairs and verify the path exists in path_file.
  local file=$1
  grep -oE '"file"[[:space:]]*:[[:space:]]*"[^"]+\.md"' "$file" 2>/dev/null |
    sed -E 's/.*"file"[[:space:]]*:[[:space:]]*"([^"]+)"/\1/' |
    while IFS= read -r ref; do
      [ -z "$ref" ] && continue
      norm=${ref#./}
      norm=${norm#wiki/}
      if ! grep -qxF "$norm" "$path_file"; then
        echo "UNRESOLVED canvas file-ref: $file -> $ref" >> "$violations_file"
      fi
    done
}

# Scan ornamental layer.
while IFS= read -r f; do
  check_wikilinks "$f"
  check_canvas_file_refs "$f"
done < <(find wiki/canvases -type f -name '*.canvas' 2>/dev/null)

while IFS= read -r f; do
  check_wikilinks "$f"
done < <(find wiki/views -type f -name '*.base' 2>/dev/null)

if [ -s "$violations_file" ]; then
  cat "$violations_file"
  count=$(wc -l < "$violations_file" | tr -d ' ')
  echo ""
  echo "$count ornamental-layer reference(s) point at non-existent markdown"
  echo "CLAUDE.md invariant: knowledge in canvas/base must also exist as .md"
  exit 1
fi
exit 0
