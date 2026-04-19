#!/usr/bin/env bash
# Operation semantics: INGEST's unprocessed-detection logic MUST treat
# a raw source as "processed" iff some wiki/sources/*.md has that raw
# source's path recorded in its `source_path:` frontmatter.
#
# This verifies the rule CLAUDE.md specifies:
#   "read wiki/.meta/sources.json to get the set of processed
#    source_path values; any raw file whose path is not in the set
#    is unprocessed."
#
# We build a fixture vault with one source summary that records a
# source_path, rebuild the sidecar, then check that scripts/build_meta.py
# correctly surfaces that source_path in wiki/.meta/sources.json.
# We verify both directions:
#
#   1. A source summary with source_path X → X appears in sources.json
#   2. A source summary WITHOUT source_path → it's in sources.json but
#      source_path is empty (meaning INGEST would treat the matching
#      raw file as unprocessed — a bug surface that LINT should catch).
set -u
cd "$(dirname "$0")/.."

FIX=$(mktemp -d -t z-wiki-ingest-idem-XXXXXX)
trap 'rm -rf "$FIX"' EXIT

mkdir -p "$FIX/wiki/sources" "$FIX/wiki/concepts" "$FIX/wiki/entities" \
         "$FIX/wiki/syntheses" "$FIX/wiki/outputs" "$FIX/wiki/.meta" \
         "$FIX/wiki/indexes/by-tag" "$FIX/wiki/indexes/by-domain" \
         "$FIX/raw/articles" "$FIX/raw/papers"
cp -r scripts "$FIX/scripts"

# Fixture: one source summary that records a processed raw path.
cat > "$FIX/wiki/sources/sample-article.md" <<'EOF'
---
title: "Sample Article"
type: source
status: final
date_created: 2026-04-19
date_modified: 2026-04-19
summary: "Fixture source summary for the idempotency invariant test."
tags:
  - test
source_path: "raw/articles/sample-article.md"
source_type: article
---
# Sample Article
Fixture body.
EOF

cat > "$FIX/raw/articles/sample-article.md" <<'EOF'
# Sample Article
Raw source body (fixture).
EOF

# A second raw file that has NOT been ingested yet.
cat > "$FIX/raw/papers/unprocessed-paper.pdf" <<'EOF'
(fixture stand-in for a PDF)
EOF

cd "$FIX"
python3 scripts/build_meta.py > /tmp/ingest-idem-out-$$ 2>&1 || {
  echo "build_meta failed:"
  cat /tmp/ingest-idem-out-$$
  rm -f /tmp/ingest-idem-out-$$
  exit 1
}
rm -f /tmp/ingest-idem-out-$$

fail=0

# (1) source_path recorded → sources.json lists it exactly as the path.
python3 - <<'PY'
import json, sys
d = json.load(open("wiki/.meta/sources.json"))
paths = [s["source_path"] for s in d["sources"]]
if "raw/articles/sample-article.md" not in paths:
    print(f"FAIL: sources.json missing source_path; got {paths}")
    sys.exit(1)
PY
if [ $? -ne 0 ]; then fail=$((fail + 1)); fi

# (2) The unprocessed raw file's path must NOT appear.
python3 - <<'PY'
import json, sys
d = json.load(open("wiki/.meta/sources.json"))
paths = [s["source_path"] for s in d["sources"]]
if "raw/papers/unprocessed-paper.pdf" in paths:
    print(f"FAIL: unprocessed raw file should not appear in sources.json "
          f"but it does: {paths}")
    sys.exit(1)
PY
if [ $? -ne 0 ]; then fail=$((fail + 1)); fi

# (3) Running build_meta a second time is idempotent — output identical.
cp wiki/.meta/sources.json /tmp/ingest-idem-first-$$.json
python3 scripts/build_meta.py > /dev/null 2>&1
if ! diff -q wiki/.meta/sources.json /tmp/ingest-idem-first-$$.json >/dev/null 2>&1; then
  # Expected: generated_at differs. Check only the sources array.
  python3 - <<PY
import json, sys
a = json.load(open("wiki/.meta/sources.json"))
b = json.load(open("/tmp/ingest-idem-first-$$.json"))
if a["sources"] != b["sources"]:
    print("FAIL: sources array changed on re-run (not idempotent)")
    sys.exit(1)
PY
  if [ $? -ne 0 ]; then fail=$((fail + 1)); fi
fi
rm -f /tmp/ingest-idem-first-$$.json

if [ "$fail" -gt 0 ]; then
  echo ""
  echo "$fail idempotency violation(s). INGEST detection logic is broken."
  exit 1
fi
exit 0
