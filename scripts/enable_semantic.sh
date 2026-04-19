#!/usr/bin/env bash
# One-shot opt-in for local semantic search.
#
#   1. Install numpy + sentence-transformers (respects active venv).
#   2. Download the embedding model (first run of sentence-transformers
#      fetches ~90MB into ~/.cache/huggingface/).
#   3. Compute embeddings for every page currently in wiki/.
#   4. Run the invariant suite to verify consistency.
#
# Idempotent: re-running is safe. Incremental embed only re-embeds pages
# whose text changed.
#
# After this runs, all commands (/wiki-ingest, /wiki-query, /wiki-lint,
# /wiki-compile, /wiki-promote) use --embed-if-enabled, which keeps
# embeddings fresh automatically on every subsequent operation.
#
# To turn it off: delete wiki/.meta/embeddings.npy and
# wiki/.meta/embeddings-manifest.tsv. Commands silently fall back to
# lexical-only search.

set -eu
cd "$(dirname "$0")/.."

echo "==> Installing optional Python deps (numpy, sentence-transformers)"
if [ -n "${VIRTUAL_ENV:-}" ]; then
  PIP="python3 -m pip"
elif command -v pipx >/dev/null 2>&1 && pipx list 2>/dev/null | grep -q z-wiki; then
  PIP="pipx inject z-wiki"
else
  PIP="python3 -m pip install --user"
fi

$PIP install -r requirements.txt

echo ""
echo "==> First embed (downloads ~90MB model on first run, then cached)"
python3 scripts/build_meta.py --embed

echo ""
echo "==> Verifying invariants"
bash scripts/check_invariants.sh

echo ""
echo "==> Semantic search is live."
echo ""
echo "Try it:"
echo "    python3 scripts/wiki_search.py \"<your query>\""
echo ""
echo "All commands now auto-maintain embeddings. To disable later,"
echo "delete wiki/.meta/embeddings.npy and embeddings-manifest.tsv."
