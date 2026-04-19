#!/usr/bin/env bash
# Unit tests for shard_index.render_type_index split logic. Runs the
# Python test harness in tests/test_shard_split.py.
#
# review.md P2: render_type_index A-H / I-P / Q-Z split path was never
# exercised by real vault data small enough to stay under the budget.
set -u
cd "$(dirname "$0")/.."
python3 tests/test_shard_split.py
