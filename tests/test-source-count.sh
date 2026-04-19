#!/usr/bin/env bash
# source_count frontmatter field on every concept/entity page matches
# the canonical backlink count in wiki/.meta/backlinks.json.
#
# Runs build_meta.py --check which computes the ground truth from
# the filesystem and compares against frontmatter.
set -u
cd "$(dirname "$0")/.."

if ! python3 scripts/build_meta.py --check; then
  exit 1
fi
exit 0
