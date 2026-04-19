#!/usr/bin/env bash
# Unit tests for wiki_search pure functions (rrf_merge, jaccard,
# dedup_and_diversify, tokenize). Runs the Python test harness in
# tests/test_search_ranking.py.
#
# review.md P2: ranking correctness had zero direct coverage.
set -u
cd "$(dirname "$0")/.."
python3 tests/test_search_ranking.py
