#!/usr/bin/env python3
"""Unit tests for the pure ranking functions in scripts/wiki_search.py.

Exercises rrf_merge, jaccard, dedup_and_diversify, and the lexical
tokenize helper without touching the filesystem or the embeddings
model. Ranking correctness is the heart of QUERY and had no direct
coverage before (review.md §3 P2).

Run standalone: python3 tests/test_search_ranking.py
Invoked by tests/test-search-ranking.sh, which check_invariants.sh
auto-discovers.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from wiki_search import (  # noqa: E402
    JACCARD_DEDUP_THRESHOLD,
    RRF_K,
    TYPE_DIVERSITY_CAP,
    dedup_and_diversify,
    jaccard,
    rrf_merge,
    tokenize,
    type_of,
)


def _check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_tokenize_drops_stopwords_and_short_tokens() -> None:
    toks = tokenize("The Attention MECHANISM is a key idea")
    _check("the" not in toks, "stopword 'the' leaked through")
    _check("is" not in toks, "stopword 'is' leaked through")
    _check("a" not in toks, "stopword 'a' leaked through")
    _check("attention" in toks, "expected 'attention' in tokens")
    _check("mechanism" in toks, "case-insensitive tokenize dropped 'mechanism'")
    # All remaining tokens must be len > 1 per wiki_search.tokenize.
    _check(all(len(t) > 1 for t in toks), f"short token slipped through: {toks}")


def test_jaccard_known_values() -> None:
    _check(jaccard("", "") == 0.0, "empty strings should yield 0.0")
    _check(jaccard("attention mechanism", "") == 0.0, "one side empty -> 0.0")
    j = jaccard("attention mechanism transformer", "attention mechanism transformer")
    _check(j == 1.0, f"identical strings should yield 1.0, got {j}")
    # Disjoint after stopword drop.
    j2 = jaccard("attention mechanism", "transformer encoder decoder")
    _check(j2 == 0.0, f"disjoint tokens should yield 0.0, got {j2}")
    # {attention, mechanism} vs {attention, decoder} -> |inter|=1, |union|=3.
    j3 = jaccard("attention mechanism", "attention decoder")
    _check(abs(j3 - (1 / 3)) < 1e-9, f"expected 1/3, got {j3}")


def test_rrf_merge_rewards_cross_list_agreement() -> None:
    # Path "a" ranks 1st in both lists -> must beat any path that ranks
    # 1st in only one list. Score formula: sum(1 / (k + rank)).
    lex = [
        {"path": "a", "title": "A"},
        {"path": "b", "title": "B"},
        {"path": "c", "title": "C"},
        {"path": "d", "title": "D"},
        {"path": "e", "title": "E"},
    ]
    sem = [
        {"path": "a", "title": "A"},
        {"path": "x", "title": "X"},
        {"path": "y", "title": "Y"},
        {"path": "z", "title": "Z"},
        {"path": "b", "title": "B"},
    ]
    merged = rrf_merge([lex, sem])
    paths = [m["path"] for m in merged]
    _check(paths[0] == "a", f"expected 'a' first, got {paths}")
    _check("b" in paths[:3], f"expected 'b' in top 3, got {paths}")
    expected_a = round(2.0 / (RRF_K + 1), 4)
    _check(
        merged[0]["score"] == expected_a,
        f"rrf score for 'a' = {merged[0]['score']}, expected {expected_a}",
    )


def test_rrf_merge_deterministic_on_tie() -> None:
    # Two disjoint single-entry lists -> identical scores; tie broken
    # by alphabetical path per wiki_search's sort key.
    merged = rrf_merge([
        [{"path": "zebra", "title": "Z"}],
        [{"path": "alpha", "title": "A"}],
    ])
    _check([m["path"] for m in merged] == ["alpha", "zebra"], merged)


def test_dedup_drops_near_duplicates() -> None:
    # Two results whose (title + summary) share most tokens collapse:
    # first is kept, second dropped by Jaccard near-dup rule.
    results = [
        {
            "path": "concepts/attention-mechanism.md",
            "title": "Attention mechanism",
            "summary": "Learned weighting over token positions",
        },
        {
            "path": "concepts/attention-mechanism-copy.md",
            "title": "Attention mechanism",
            "summary": "Learned weighting over token positions",
        },
        {
            "path": "concepts/transformer.md",
            "title": "Transformer",
            "summary": "Architecture built on attention",
        },
    ]
    kept = dedup_and_diversify(results, limit=5)
    paths = [r["path"] for r in kept]
    _check(
        "concepts/attention-mechanism.md" in paths,
        "first near-dup must be retained",
    )
    _check(
        "concepts/attention-mechanism-copy.md" not in paths,
        "near-duplicate must be dropped",
    )
    _check(
        "concepts/transformer.md" in paths,
        "unrelated result must survive dedup",
    )
    _check(JACCARD_DEDUP_THRESHOLD == 0.85, "dedup threshold drifted from 0.85")


def test_diversity_cap_caps_overrepresented_type() -> None:
    # Force 10 source-type results with limit=10 and cap=0.6 -> only 6
    # sources should land. Pad with concepts so fill-pass can reach 10.
    results: list[dict] = []
    for i in range(10):
        results.append({
            "path": f"wiki/sources/src-{i}.md",
            "title": f"Source {i}",
            "summary": f"Unique summary token src{i}",
        })
    for i in range(10):
        results.append({
            "path": f"wiki/concepts/con-{i}.md",
            "title": f"Concept {i}",
            "summary": f"Unique summary token con{i}",
        })

    kept = dedup_and_diversify(results, limit=10)
    by_type = Counter(type_of(r["path"]) for r in kept)
    cap = max(1, int(10 * TYPE_DIVERSITY_CAP))
    _check(
        by_type["sources"] == cap,
        f"sources should be capped at {cap}, got {by_type['sources']} (kept={kept})",
    )
    _check(len(kept) == 10, f"expected 10 kept, got {len(kept)}")


def main() -> int:
    tests = [
        test_tokenize_drops_stopwords_and_short_tokens,
        test_jaccard_known_values,
        test_rrf_merge_rewards_cross_list_agreement,
        test_rrf_merge_deterministic_on_tie,
        test_dedup_drops_near_duplicates,
        test_diversity_cap_caps_overrepresented_type,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    if failed:
        print(f"{failed}/{len(tests)} tests failed")
        return 1
    print(f"all {len(tests)} ranking tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
