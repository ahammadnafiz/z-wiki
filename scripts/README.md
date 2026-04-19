# scripts/ — z-wiki tooling

Zero third-party dependencies. Python 3 standard library + `rg`
(ripgrep) + standard Unix tools only. Safe to run on any machine
that has the vault cloned.

## Files

| Script | Purpose | Invoked by |
|---|---|---|
| `build_meta.py` | Rebuild `wiki/.meta/*` from filesystem. Idempotent. | `/wiki-ingest` post-pass, `/wiki-compile`, `/wiki-lint` |
| `shard_index.py` | Rebuild `wiki/index.md` + per-type `_index.md` + `wiki/indexes/by-tag/*` + `wiki/indexes/by-domain/*`. | `/wiki-compile`, `/wiki-lint` |
| `wiki_search.py` | Grep-first ranked search over `wiki/.meta/search-index.tsv`. CLI substrate for `/wiki-search` and `/wiki-query`. | `/wiki-query`, `/wiki-search` |
| `check_invariants.sh` | Run every test in `tests/`. Exits non-zero on any failure. | CI; manual pre-ingest check |

## Usage

```bash
# Rebuild the sidecar cache (safe, idempotent).
python3 scripts/build_meta.py

# Rebuild sharded indexes after a batch of ingests.
python3 scripts/shard_index.py

# Search the wiki (grep-first, BM25-style ranking).
python3 scripts/wiki_search.py "attention mechanism transformer"

# Run the invariant test suite.
bash scripts/check_invariants.sh
```

## Why Python, not pure shell

Backlink graphs + JSON writes get messy in bash. Python stdlib keeps
dependencies at zero while letting the logic stay readable. Every
script finishes in under a second on a 5K-page vault because the
work is bounded by filesystem reads, not CPU.

## Extension points

- **Semantic search.** `wiki_search.py --semantic` is a hook that
  currently falls back to keyword mode. To enable embeddings, add a
  `scripts/semantic.py` that takes a query and returns ranked paths;
  `wiki_search.py` will prefer it when `--semantic` is passed. Keep
  the dep optional — the grep path is the default.
- **Incremental meta.** `build_meta.py --only <path>` updates only
  one source's outbound links. Used by `/wiki-ingest` to avoid a
  full rebuild on every source.
