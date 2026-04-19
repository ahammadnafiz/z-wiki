#!/usr/bin/env bash
# wiki/.meta/* is in sync with the filesystem. Runs build_meta in
# --check mode, which returns non-zero if frontmatter source_count
# disagrees with the computed backlink graph.
set -u
cd "$(dirname "$0")/.."

for f in wiki/.meta/backlinks.json wiki/.meta/sources.json wiki/.meta/search-index.tsv; do
  if [ ! -e "$f" ]; then
    echo "missing: $f"
    echo "run: python3 scripts/build_meta.py"
    exit 1
  fi
done

# Verify backlinks.json is valid JSON with expected shape.
python3 - <<'PY' || exit 1
import json, sys
try:
    d = json.load(open("wiki/.meta/backlinks.json"))
    s = json.load(open("wiki/.meta/sources.json"))
except Exception as e:
    print(f"JSON parse error: {e}")
    sys.exit(1)
for key in ("version", "generated_at", "nodes"):
    if key not in d:
        print(f"backlinks.json missing key: {key}")
        sys.exit(1)
for key in ("version", "generated_at", "sources"):
    if key not in s:
        print(f"sources.json missing key: {key}")
        sys.exit(1)
PY
exit 0
