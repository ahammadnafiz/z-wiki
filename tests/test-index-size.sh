#!/usr/bin/env bash
# wiki/index.md stays under the 10K-token graduation threshold. If it
# exceeds, sharding is failing and QUERY will pay the tax on every
# call. This is the forcing function that keeps the top-level index
# thin.
#
# Threshold: 40K characters (~10K tokens at 4 chars/token).
set -u
cd "$(dirname "$0")/.."

f=wiki/index.md
[ -f "$f" ] || { echo "$f missing"; exit 2; }

chars=$(wc -c < "$f" | tr -d ' ')
limit=40000

if [ "$chars" -gt "$limit" ]; then
  tokens=$(( chars / 4 ))
  echo "wiki/index.md is $chars chars (~$tokens tokens), exceeds $limit char limit"
  echo "run: python3 scripts/shard_index.py"
  exit 1
fi
exit 0
