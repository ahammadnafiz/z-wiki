#!/usr/bin/env bash
# Every wiki page starts with a YAML frontmatter block containing the
# required fields: title, type, status, date_created (or
# date_modified for generated pages), summary, tags.
set -u
cd "$(dirname "$0")/.."

violations=0
while IFS= read -r f; do
  case "$(basename "$f")" in
    _index*.md|README.md) continue ;;
  esac
  head=$(head -30 "$f")
  # Must start with '---' on line 1.
  if ! echo "$head" | head -1 | grep -qE '^---\s*$'; then
    echo "$f: missing frontmatter opener"
    violations=$((violations + 1))
    continue
  fi
  for field in title type status summary; do
    if ! echo "$head" | grep -qE "^${field}:"; then
      echo "$f: missing field '$field'"
      violations=$((violations + 1))
    fi
  done
  if ! echo "$head" | grep -qE '^tags:'; then
    echo "$f: missing 'tags:' block"
    violations=$((violations + 1))
  fi
done < <(
  find wiki \
    \( -path wiki/.meta -o -path wiki/attachments -o -path wiki/canvases -o -path wiki/views \) -prune -o \
    -type f -name '*.md' -print
)

[ "$violations" -gt 0 ] && exit 1
exit 0
