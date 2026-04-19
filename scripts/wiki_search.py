#!/usr/bin/env python3
"""Ranked search over the z-wiki sidecar cache.

Three modes, auto-selected:

    lexical    BM25-style keyword search over wiki/.meta/search-index.tsv.
               Always available. Zero deps beyond Python stdlib.

    semantic   Cosine-similarity over wiki/.meta/embeddings.npy.
               Requires numpy + sentence-transformers (optional).

    hybrid     Runs both, merges with Reciprocal Rank Fusion (k=60).
               This is the default when embeddings exist.

Post-ranking stages (applied to all modes):
    1. Type diversity cap — no single type (sources/concepts/entities/
       syntheses/outputs) exceeds 60% of top N.
    2. Jaccard near-dup dedup — drops any result whose (title+summary)
       Jaccard similarity to a higher-ranked result exceeds 0.85.

Usage:
    python3 scripts/wiki_search.py "attention mechanism"
    python3 scripts/wiki_search.py --mode lexical "attention"
    python3 scripts/wiki_search.py --mode semantic "attention"
    python3 scripts/wiki_search.py --mode hybrid "attention"
    python3 scripts/wiki_search.py --type concepts "attention"
    python3 scripts/wiki_search.py --tag transformers "attention"
    python3 scripts/wiki_search.py --json --limit 20 "attention"
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

FIELD_WEIGHTS = {
    "title": 3.0,
    "tags": 2.0,
    "concepts": 2.0,
    "summary": 1.0,
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "to",
    "what", "which", "who", "why", "with",
}

# SHARED CONTRACT with scripts/build_meta.py — keep aligned.
# build_meta.py writes wiki/.meta/search-index.tsv with raw (un-tokenized)
# field values in the order: path \t title \t tags \t concepts \t summary.
# Tokenization is query-time only; this regex must accept the characters
# build_meta emits (slug kebab-case, bracketed wikilinks, space-joined tags)
# after .lower(). Brackets `[[ ]]` are stripped by the character class; the
# slug chars inside survive. Changing either side alone will silently degrade
# retrieval — update both files together.
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]*")

RRF_K = 60
JACCARD_DEDUP_THRESHOLD = 0.85
TYPE_DIVERSITY_CAP = 0.6   # no single type > 60% of top N


# --------------------------------------------------------------------------
# Lexical (BM25-ish) search
# --------------------------------------------------------------------------

def tokenize(s: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(s.lower()) if t not in STOPWORDS and len(t) > 1]


def parse_line(line: str) -> dict:
    parts = line.rstrip("\n").split("\t")
    while len(parts) < 5:
        parts.append("")
    return {
        "path": parts[0],
        "title": parts[1],
        "tags": parts[2],
        "concepts": parts[3],
        "summary": parts[4],
    }


def lexical_score(entry: dict, query_tokens: list[str], idf: dict[str, float]) -> float:
    if not query_tokens:
        return 0.0
    fields = {
        "title": tokenize(entry["title"]),
        "tags": tokenize(entry["tags"]),
        "concepts": tokenize(entry["concepts"]),
        "summary": tokenize(entry["summary"]),
    }
    total = 0.0
    for tok in query_tokens:
        for field, field_tokens in fields.items():
            tf = field_tokens.count(tok)
            if tf == 0:
                continue
            weight = FIELD_WEIGHTS[field]
            dampened = tf / (tf + 1.5)
            total += weight * dampened * idf.get(tok, 1.0)
    return total


def build_idf(entries: list[dict]) -> dict[str, float]:
    N = max(len(entries), 1)
    df: Counter[str] = Counter()
    for e in entries:
        terms: set[str] = set()
        for f in ("title", "tags", "concepts", "summary"):
            terms.update(tokenize(e[f]))
        for t in terms:
            df[t] += 1
    return {t: math.log((N - n + 0.5) / (n + 0.5) + 1.0) for t, n in df.items()}


def filter_entries(
    entries: list[dict],
    type_filter: str | None,
    tag_filter: str | None,
) -> list[dict]:
    out = []
    for e in entries:
        if type_filter and f"/{type_filter}/" not in e["path"]:
            continue
        if tag_filter:
            tags = set(tokenize(e["tags"]))
            if tag_filter.lower() not in tags:
                continue
        out.append(e)
    return out


def load_lexical_index(vault: Path) -> list[dict]:
    tsv = vault / "wiki" / ".meta" / "search-index.tsv"
    if not tsv.exists():
        print(
            "error: wiki/.meta/search-index.tsv missing — run "
            "`python3 scripts/build_meta.py` first",
            file=sys.stderr,
        )
        sys.exit(2)
    entries: list[dict] = []
    with tsv.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entries.append(parse_line(line))
    return entries


def lexical_search(
    query: str,
    *,
    vault: Path,
    type_filter: str | None,
    tag_filter: str | None,
    raw_limit: int,
) -> list[dict]:
    entries = filter_entries(load_lexical_index(vault), type_filter, tag_filter)
    idf = build_idf(entries)
    tokens = tokenize(query)
    scored = [(lexical_score(e, tokens, idf), e) for e in entries]
    scored = [(s, e) for s, e in scored if s > 0]
    scored.sort(key=lambda x: (-x[0], x[1]["path"]))
    return [
        {
            "path": e["path"],
            "title": e["title"],
            "tags": [t for t in e["tags"].split() if t],
            "summary": e["summary"],
            "score": round(s, 4),
        }
        for s, e in scored[:raw_limit]
    ]


# --------------------------------------------------------------------------
# Semantic search (optional)
# --------------------------------------------------------------------------

def semantic_search(
    query: str,
    *,
    vault: Path,
    type_filter: str | None,
    tag_filter: str | None,
    raw_limit: int,
) -> list[dict]:
    sys.path.insert(0, str(vault / "scripts"))
    try:
        import semantic  # local module
        return semantic.search(
            query,
            vault=vault,
            limit=raw_limit,
            type_filter=type_filter,
            tag_filter=tag_filter,
        )
    except ImportError as e:
        print(
            f"semantic search unavailable ({e}); falling back to lexical",
            file=sys.stderr,
        )
        return []


def embeddings_present(vault: Path) -> bool:
    return (vault / "wiki" / ".meta" / "embeddings.npy").exists() \
        and (vault / "wiki" / ".meta" / "embeddings-manifest.tsv").exists()


# --------------------------------------------------------------------------
# Merge + dedup
# --------------------------------------------------------------------------

def rrf_merge(ranked_lists: list[list[dict]], k: int = RRF_K) -> list[dict]:
    """Reciprocal Rank Fusion. Each list is a ranked list of dicts
    keyed by 'path'. Returns one merged list sorted by RRF score."""
    by_path: dict[str, dict] = {}
    rrf_scores: dict[str, float] = defaultdict(float)

    for ranked in ranked_lists:
        for rank, entry in enumerate(ranked, start=1):
            path = entry["path"]
            rrf_scores[path] += 1.0 / (k + rank)
            if path not in by_path:
                by_path[path] = dict(entry)

    merged = []
    for path, score in rrf_scores.items():
        item = dict(by_path[path])
        item["score"] = round(score, 4)
        merged.append(item)
    merged.sort(key=lambda x: (-x["score"], x["path"]))
    return merged


def jaccard(a: str, b: str) -> float:
    ta = set(tokenize(a))
    tb = set(tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def type_of(path: str) -> str:
    for t in ("sources", "concepts", "entities", "syntheses", "outputs"):
        if f"/{t}/" in path:
            return t
    return "other"


def dedup_and_diversify(results: list[dict], limit: int) -> list[dict]:
    """Apply Jaccard near-dup dedup and type-diversity cap."""
    if not results:
        return results

    cap = max(1, int(limit * TYPE_DIVERSITY_CAP))
    kept: list[dict] = []
    type_counts: Counter[str] = Counter()

    for r in results:
        if len(kept) >= limit:
            break

        # Jaccard near-dup check against already-kept items.
        signature = f"{r.get('title', '')} {r.get('summary', '')}"
        is_dup = False
        for k in kept:
            k_sig = f"{k.get('title', '')} {k.get('summary', '')}"
            if jaccard(signature, k_sig) >= JACCARD_DEDUP_THRESHOLD:
                is_dup = True
                break
        if is_dup:
            continue

        # Type diversity cap.
        t = type_of(r["path"])
        if type_counts[t] >= cap:
            # Hold this one; maybe a later pass picks it up if we end
            # up under-filled. Simple heuristic: skip it.
            continue

        kept.append(r)
        type_counts[t] += 1

    # If diversity cap left us short, fill with whatever's left (preserving order).
    if len(kept) < limit:
        held = [r for r in results if r not in kept]
        for r in held:
            if len(kept) >= limit:
                break
            # Still enforce Jaccard even in the fill pass.
            signature = f"{r.get('title', '')} {r.get('summary', '')}"
            dup = any(
                jaccard(signature, f"{k.get('title', '')} {k.get('summary', '')}")
                >= JACCARD_DEDUP_THRESHOLD
                for k in kept
            )
            if dup:
                continue
            kept.append(r)

    return kept


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _emit(results: list[dict], as_json: bool, note: str = "") -> None:
    if as_json:
        print(json.dumps(results, indent=2))
        return
    if note:
        print(f"# {note}\n")
    if not results:
        print("no matches")
        return
    for r in results:
        tag_str = " ".join(f"#{t}" for t in r["tags"]) if r.get("tags") else ""
        summary = r.get("summary", "") or ""
        if len(summary) > 140:
            summary = summary[:137] + "..."
        score = r.get("score", 0.0)
        print(f"{score:>6.3f}  {r['path']}")
        print(f"         {r['title']}  {tag_str}".rstrip())
        if summary:
            print(f"         {summary}")
        print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="+")
    ap.add_argument("--vault", default=".")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--type", dest="type_filter",
                    help="restrict to a page type (sources/concepts/entities/syntheses/outputs)")
    ap.add_argument("--tag", dest="tag_filter", help="restrict to a tag")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument(
        "--mode",
        choices=("auto", "lexical", "semantic", "hybrid"),
        default="auto",
        help="auto: hybrid if embeddings exist else lexical",
    )
    # Legacy alias; kept so older prompts keep working.
    ap.add_argument("--semantic", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    vault = Path(args.vault).resolve()
    query = " ".join(args.query).strip()

    mode = args.mode
    if args.semantic and mode == "auto":
        mode = "semantic"
    if mode == "auto":
        mode = "hybrid" if embeddings_present(vault) else "lexical"

    # Pull ~2x limit from each source so merge+dedup has material to work with.
    raw_limit = max(args.limit * 2, 20)

    lex: list[dict] = []
    sem: list[dict] = []

    if mode in ("lexical", "hybrid"):
        lex = lexical_search(
            query, vault=vault,
            type_filter=args.type_filter, tag_filter=args.tag_filter,
            raw_limit=raw_limit,
        )
    if mode in ("semantic", "hybrid"):
        sem = semantic_search(
            query, vault=vault,
            type_filter=args.type_filter, tag_filter=args.tag_filter,
            raw_limit=raw_limit,
        )
        # If hybrid was requested but semantic returned empty (library
        # missing or index not built), fall back to lexical-only.
        if mode == "hybrid" and not sem and not lex:
            lex = lexical_search(
                query, vault=vault,
                type_filter=args.type_filter, tag_filter=args.tag_filter,
                raw_limit=raw_limit,
            )

    if mode == "hybrid":
        merged = rrf_merge([lst for lst in (lex, sem) if lst])
    elif mode == "semantic":
        merged = sem
    else:
        merged = lex

    results = dedup_and_diversify(merged, args.limit)

    note = ""
    if mode == "hybrid" and not sem:
        note = "hybrid requested; semantic unavailable — lexical only"
    _emit(results, args.as_json, note=note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
