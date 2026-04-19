#!/usr/bin/env bash
# Drift test: z-wiki's parse_frontmatter() vs PyYAML's yaml.safe_load.
# Runs the Python harness in tests/test_frontmatter_drift.py, which
# self-skips if PyYAML isn't installed (it's an optional tooling dep).
#
# review.md P2: guards against silent data loss in the hand-rolled parser.
set -u
cd "$(dirname "$0")/.."
python3 tests/test_frontmatter_drift.py
