# z-wiki Architecture Review

**Date:** 2026-04-19
**Reviewer:** Claude (opus-4-7, `/plan-eng-review`)
**Scope:** 2,175 LOC (5 Python scripts + 11 bash invariant tests) defining INGEST / QUERY / LINT / COMPILE / PROMOTE operations, a sidecar cache (`wiki/.meta/`), sharded indexes (`wiki/indexes/`, per-type `_index.md`), and opt-in hybrid search (lexical BM25-ish + local sentence-transformers via RRF).

**Current vault size:** 0 real sources (scaffolding only). Design target: thousands of sources.

---

## Executive summary

The **architecture is well-designed for its scale target** — the sidecar + thin-index + hybrid-first triad is the right shape, and the invariants enforce it. Code quality is solid: stdlib-first, no speculative abstractions, atomic writes, clean separation. The main risks are **cold-start cost of the complexity** (you're maintaining ~2.2K lines before the first real query), **a few correctness gaps in drift handling**, and a **distribution story that's currently "clone the repo"**.

---

## 1. Architecture Review

### Strengths

**Thin-index + sidecar is the right architecture.** `wiki/index.md` <1K tokens, `search-index.tsv` as grep substrate, `backlinks.json` as inverse graph — all regenerated atomically from markdown as ground truth. At 2,000 sources the naive "load index.md on every QUERY" would cost ~40K tokens per call; you avoid that by construction. [Layer 1 / boring by default]

**Source-of-truth discipline.** Markdown frontmatter + wikilinks are authoritative; `.meta/` is derived and disposable. LINT reconciles drift. This is the right invariant — stated clearly in CLAUDE.md:18-26 and enforced by `check_drift()` in `build_meta.py:242`.

**Promotion is user-gated.** `/wiki-promote` only, never auto-triggered from INGEST or LINT. Prevents Claude from silently burning tokens expanding stubs that aren't load-bearing. Strong product instinct.

**Retrieval ladder is well-specified.** CLAUDE.md:237-248 spells out grep → tag shard → type catalog → `index.md` fallback. Each rung bounded by token cost. This is the thing most RAG systems get wrong.

**Hybrid search with RRF k=60 is standard, not exotic.** `wiki_search.py:214` — you used the known-good constant. Type-diversity cap at 60% and Jaccard 0.85 dedup are reasonable. [Layer 1]

### Concerns

**[P1] (confidence: 9/10) Globally-unique slug invariant is load-bearing but only weakly enforced.**

Filenames collide → wikilinks silently resolve to the wrong page. `build_meta.py:126` builds `page_by_slug = {slug_of(p): p for p in pages}` — if two pages share a stem, the second overwrites the first with no warning. `tests/test-unique-slugs.sh` catches this *after* the fact, but `build_meta.py` will happily produce a corrupted backlinks graph in the meantime.

**Recommendation:** Make `build_meta.py` detect slug collisions and fail loudly (or emit to stderr) rather than silently last-write-wins. 3 lines of code. [Layer 3 — explicit is cheap here, implicit is catastrophic]

**[P1] (confidence: 8/10) INGEST post-pass is described, but nothing in the code executes it.**

CLAUDE.md:346-360 specifies an atomic whole-vault post-pass (rebuild `.meta/`, reconcile frontmatter drift, list promotion candidates, stamp `last_seen`). That's a Claude-executed protocol, not a script. Means: if a future Claude session skips a step (e.g. forgets to bump `last_seen` on an appended page), there's no enforcement. LINT catches drift eventually but only on the schedule the user runs it.

**Recommendation:** Either (a) add `scripts/ingest_postpass.py` that does the deterministic parts (rebuild sidecar, reconcile `source_count`, stamp `last_seen` based on git diff), or (b) accept the protocol as prose and add a LINT-fail invariant that catches stale `last_seen` on pages with recent commits. Option (a) is the complete version. [Boring by default — deterministic over prose instruction]

**[P2] (confidence: 8/10) No INGEST script exists; it's pure prose protocol.**

Same class of concern as above, broader: INGEST is a 60-line procedural spec in CLAUDE.md, executed by Claude. Batch-size dispatch, token-gating for 50k/200k cutoffs, subagent-per-source for batches of 3+ — all of this is instruction, not code. The invariant tests catch filesystem state but can't catch "Claude ingested only 4 of 7 sources and claimed done."

**Recommendation:** For deterministic parts (detecting unprocessed sources, extraction via `markitdown`, token counting, batch planning), consider a thin `scripts/ingest_plan.py` that emits a structured plan Claude then executes. Keeps the LLM doing judgment work (summary, concept extraction, contradiction flagging) and moves the bookkeeping out of the prompt. Feel free to defer.

**[P2] (confidence: 9/10) Promotion thresholds evaluate `inbound_refs` from any page.**

CLAUDE.md:440-449: `inbound_refs >= 5` promotes a stub. But `inbound_refs` includes outputs, syntheses, and other stubs — all of which are Claude-written downstream artifacts. A single QUERY that cites a stub 5 times would auto-qualify that stub for promotion even though the "load-bearing" signal is entirely self-generated.

**Recommendation:** Either scope `inbound_refs` to sources+concepts+entities (exclude outputs/syntheses from the count), or raise the threshold, or flag "5 refs but 0 from sources" as suspicious in promotion candidates. I'd do the first: `inbound_refs_primary = inbound_sources + inbound_concepts + inbound_entities`. [Layer 3 — the standard "count all inbound links" approach is wrong for this system because Claude's own outputs inflate it]

**[P2] (confidence: 7/10) No distribution / portability story.**

The repo is designed for one user on one machine. No package (pip-installable), no CI running invariants on push, no GitHub Action enforcing `check_invariants.sh` on PRs. If you want others to use z-wiki, they clone it and copy scripts manually. If you want yourself to use it across machines, state sync is implicit in git.

**Recommendation:** Bare minimum — add a GitHub Action that runs `scripts/check_invariants.sh` on every push. That catches drift the moment it's committed instead of next LINT. ~20 lines of YAML. Broader packaging is a follow-up.

**[P3] (confidence: 6/10) Ornamental layer (Bases + Canvas) is declared non-load-bearing but not mechanically separated.**

CLAUDE.md:50-58 says `.base` and `.canvas` must never become primary navigation, and any knowledge in canvas must also exist in markdown. But nothing enforces it — a future Claude (or user) could quietly make a `.base` the only listing of some category. The invariant is prose.

**Recommendation:** Add a test that scans `wiki/views/*.base` and `wiki/canvases/*.canvas` for wikilinks whose target exists *only* in a canvas/base. Cheap to write, prevents the drift. Low priority while you're the only user.

### Data-flow diagram

```
  raw/*.{md,pdf,docx,...}  ─┐
                             │  INGEST (Claude + markitdown)
                             ▼
             wiki/sources/*.md   ─┐
             wiki/concepts/*.md  ─┼─ markdown = source of truth
             wiki/entities/*.md  ─┘
                             │
                             │  build_meta.py (stdlib only)
                             ▼
                 wiki/.meta/backlinks.json
                 wiki/.meta/sources.json
                 wiki/.meta/search-index.tsv
                 wiki/.meta/embeddings.npy   (opt-in)
                 wiki/.meta/embeddings-manifest.tsv
                             │
                             │  shard_index.py
                             ▼
                   wiki/index.md           (< 1K tokens)
                   wiki/<type>/_index.md   (auto-sharded @ 10K)
                   wiki/indexes/by-tag/*.md
                             │
                             │  QUERY
                             ▼
           wiki_search.py ──► semantic.py (if embeddings)
                   │                │
                   └── RRF merge ◄──┘
                        │
                        ▼
             wiki/outputs/{question-slug}.md
```

---

## 2. Code Quality Review

### Strengths

- **Stdlib-first.** `build_meta.py` is pure Python stdlib, no YAML parser (hand-rolled for the subset you use, which is honest — you're not pretending to be a general YAML parser).
- **Atomic writes everywhere.** Every write uses `tmp.replace(target)`. Good.
- **Clear separation.** `build_meta.py` = derive sidecar. `shard_index.py` = derive indexes. `wiki_search.py` = query. `semantic.py` = embeddings. Single-responsibility, call graph is flat.
- **Lazy imports** (`numpy`, `sentence_transformers` imported at call-site, not module-top). Keeps lexical path dep-free.
- **`--check` mode** on `build_meta.py` for CI-style drift detection. Thoughtful.

### Issues

**[P1] (confidence: 9/10) `build_meta.py:342` — `np.load()` uses default which allows arbitrary-object deserialization.**

If `embeddings.npy` is ever tampered with (malicious PR, disk corruption, format change), numpy's default loader permits deserializing arbitrary Python objects — which is effectively arbitrary code execution at load time. You already know to trust your own output, but this is a 1-argument fix:

```python
old_matrix = np.load(mat_path, allow_pickle=False) if mat_path.exists() else None
```

Same fix in `semantic.py:77`.

**[P2] (confidence: 9/10) `build_meta.py:39` — `FRONTMATTER_RE.match` only matches at buffer start.**

If a page has a BOM or a leading blank line before `---`, frontmatter silently parses as empty dict. The LINT frontmatter test might catch it; the sidecar builder will not. Quick fix: strip BOM / leading whitespace before match, or use `re.search` with a `^` anchor and MULTILINE.

**[P2] (confidence: 7/10) `parse_frontmatter()` hand-rolled.**

Honest but fragile. It handles scalars + list-of-scalars. If a future template adds a nested dict (e.g. `sources_cited: {foo: bar}`), silent data loss. Two options:
- Depend on PyYAML (adds 1 transitive dep, well-known library, fine). [Layer 1]
- Add an invariant test that every frontmatter parses identically under this parser and `yaml.safe_load`, caught drift immediately.

I'd do the second — you've already written a working parser; just gate its continued correctness. ~15 lines.

**[P2] (confidence: 8/10) `shard_index.py:53` — imports `build_meta` via `sys.path.insert`.**

Works, but means `scripts/` is not a package. Later if you add typing or a test harness that imports these cross-wise, it'll get awkward. Simple fix: `scripts/__init__.py` and `from scripts.build_meta import parse_frontmatter`. Or, pragmatically, leave it — the current mess is ~3 lines and contained.

**[P3] (confidence: 7/10) `wiki_search.py:162` — sort key `(-score, path)` when scores are floats.**

Tiebreak by path is fine, but with BM25-style scores you occasionally get identical scores across many entries (common terms, small vault). Path-alphabetical tiebreak means `a-concept` always beats `z-concept` on ties, not semantic relevance. Consider tiebreaking by `len(path)` descending (deeper = more specific) or by `source_count` descending. Low-priority polish.

**[P3] (confidence: 8/10) Hardcoded constants scattered across modules.**

`RRF_K = 60`, `JACCARD_DEDUP_THRESHOLD = 0.85`, `TYPE_DIVERSITY_CAP = 0.6` in `wiki_search.py:55-57`; `SHARD_TOKEN_BUDGET = 10_000`, `TAG_MIN_MEMBERS = 3` in `shard_index.py:29-31`. Fine for a solo project, but if you ever tune these, they're scattered. Consider a `scripts/config.py` with all tunables. Don't refactor until you're changing more than one.

**[P3] (confidence: 6/10) No type hints on return dicts.**

`build()` returns `dict` with a specific shape that every caller relies on. Consider a `TypedDict` for it, or a dataclass. Makes future changes safer. Very low priority.

### DRY check

Tokenization lives in `wiki_search.py:64` (lexical) and `search-index.tsv` construction in `build_meta.py:194-204`. Different tokenizers = mismatched retrieval. Right now they're not wildly inconsistent (both split on word chars, lowercase), but `wiki_search.py` applies STOPWORDS, `build_meta.py` does not. That's intentional (stopwords are query-time), but the split rule should be identical. Worth a shared helper or at least a comment noting they must stay aligned.

---

## 3. Test Review

### Coverage diagram

```
CORE CODEPATH COVERAGE (scripts/)
==========================================
[+] build_meta.py
    ├── parse_frontmatter()        [GAP] — no direct test
    │                              Covered transitively via test-frontmatter,
    │                              test-source-count. Acceptable.
    ├── body_wikilinks()           [GAP] — no direct test
    │                              Covered transitively via test-wikilinks-resolve.
    ├── build()                    [★★  TESTED]  test-meta-consistent, test-source-count
    ├── check_drift()              [★   TESTED]  test-meta-consistent (shape only)
    ├── embed_pages()              [★★  TESTED]  test-embeddings-consistent
    │   └── BUG_REGRESSION         [GAP] — the np.save tmp-path bug
    │                                      you just fixed has no regression test.
    │                                      CRITICAL — write this test.
    └── write_meta()               [★   TESTED]  implicit via meta-consistent

[+] shard_index.py
    ├── render_top_index()         [★   TESTED]  test-index-size (size cap only)
    ├── render_type_index()        [GAP] — no test exercises the >10K shard split
    │                              Cannot be triggered at current vault size
    │                              but the alphabetical bucketing is untested.
    ├── render_tag_shards()        [GAP] — no test that #tag with <3 members is excluded
    └── TAG_MIN_MEMBERS logic      [GAP]

[+] wiki_search.py
    ├── lexical_search()           [GAP] — no test asserting specific ranking
    ├── semantic_search()          [GAP] — no test
    ├── rrf_merge()                [GAP] — no test with known-overlap inputs
    ├── dedup_and_diversify()      [GAP] — no test asserting cap is enforced
    └── jaccard()                  [GAP] — pure function, trivially testable

[+] semantic.py
    ├── load_index()               [★   TESTED]  via test-embeddings-consistent
    ├── embed_query()              [GAP] — requires model, skip
    └── search()                   [GAP] — integration path untested

INVARIANT SUITE (11 tests, all currently PASS)
==========================================
✓ frontmatter, kebab-case, unique-slugs, source-path-unique,
  source-count, meta-consistent, wikilinks-resolve, index-size,
  ingest-idempotent, outputs-citations-resolve, embeddings-consistent

─────────────────────────────────────────────
COVERAGE: invariants strong, unit coverage weak
  Filesystem invariants:  11/11 present (excellent)
  Pure-function units:    ~2/20 (most untested)
  Ranking correctness:    0 tests
─────────────────────────────────────────────
```

### Findings

**[P1 — REGRESSION] (confidence: 10/10) Write a regression test for the `np.save` tmp-path bug.**

Bug fixed in commit `12c341a`. Cause: `np.save(Path("x.npy.tmp"), arr)` writes to `x.npy.tmp.npy`, breaking `tmp.replace(mat_path)`. **This is the exact case the REGRESSION RULE covers — no discussion, write the test.**

Suggested test (`tests/test-embeddings-tmp-path.sh`):

```bash
#!/usr/bin/env bash
# Regression: np.save must write to the exact tmp path we gave it.
# Bug fixed in 12c341a: np.save auto-appends .npy when given a Path,
# creating embeddings.npy.tmp.npy and breaking the atomic rename.
set -eu
cd "$(dirname "$0")/.."

# Run embed rebuild; must leave no stray .tmp* files behind.
python3 scripts/build_meta.py --embed >/dev/null 2>&1 || {
  echo "build failed"; exit 1;
}
strays=$(find wiki/.meta -name 'embeddings.npy.tmp*' 2>/dev/null)
if [ -n "$strays" ]; then
  echo "stray tmp files after embed:"
  echo "$strays"
  exit 1
fi
exit 0
```

**[P2] (confidence: 8/10) `rrf_merge` and `dedup_and_diversify` have zero direct tests.**

These are the ranking-correctness heart of QUERY. Pure functions with deterministic inputs. Easy to test. A 30-line pytest-style test covering:
- RRF: same path ranked 1st in both lists → higher score than path ranked 1st in one + 5th in other.
- Dedup: two results with Jaccard(title+summary) > 0.85 → second one dropped.
- Diversity: force 10 source-type results → only 6 survive at `limit=10`.

No test here means silently wrong retrieval is possible after any tuning.

**[P2] (confidence: 7/10) `render_type_index` shard split is untested.**

Logic at `shard_index.py:176-214` only fires when a type's body exceeds 40K chars. At current scale (0 entries), never executes. Easy to fake-test by constructing a synthetic entry list and calling `render_type_index` directly — confirms the a-h/i-p/q-z bucketing and the parent-pointer structure are correct.

**[P3] (confidence: 6/10) Ranking quality has no eval.**

You have correctness tests (structural) but no "does the retrieval return the right thing" test. Given the vault is empty, not actionable today. When you have 50+ sources, add 5-10 canned queries with known-good expected paths and assert they're in the top-5.

---

## 4. Performance Review

### Current profile

At 0 sources, everything is instant. Projections at 2K sources:

- **`build_meta.py`** — O(N) filesystem walk + O(N·avg_links) wikilink resolution. At 2K sources × avg 20 wikilinks = 40K regex runs. Sub-second on modern hardware.
- **`wiki_search.py` lexical** — O(N) over `search-index.tsv` per query. Each page ~200 bytes of indexed text. 2K × 200 = 400KB to scan. ~5ms.
- **`semantic.py`** — `matrix @ q` is O(N·384). 2K × 384 float32 = ~3MB. ~1ms dot product. Model load (~90MB all-MiniLM-L6-v2) dominates; cached in `_MODEL_CACHE`.
- **`shard_index.py`** — O(N) read frontmatter heads + O(N) write. Fine.
- **Embedding rebuild** — incremental via SHA cache. Only pages with changed text re-encode. Good.

### Findings

**[P2] (confidence: 8/10) `shard_index.py:50` re-parses frontmatter for every page, redundantly.**

`build_meta.py:build()` already has `page_fm` in memory with parsed frontmatter. `shard_index.py` re-reads every page's head and re-parses. At 2K pages: 2x the frontmatter parse work per `/wiki-compile`. Not a blocker but an obvious optimization.

**Recommendation:** Have `build_meta.py` also emit a `page-fm.json` to `.meta/`, or merge `shard_index` into the `build_meta` pipeline so they share one parse pass. The second is cleaner — one command, one walk.

**[P2] (confidence: 8/10) `build_idf()` rebuilds IDF on every query.**

`wiki_search.py:102-111`. At 2K entries, it's a 2K-entry Counter rebuild plus tokenization of every field of every entry, per query. Probably 20-50ms at 2K scale. Small, but avoidable.

**Recommendation:** Persist IDF to `wiki/.meta/idf.json` as part of `build_meta.py`. Query-time just loads it. Also keeps IDF stable across queries within a vault snapshot (minor correctness win).

**[P3] (confidence: 7/10) `jaccard()` is re-tokenizing on every comparison in `dedup_and_diversify`.**

`wiki_search.py:236`. Nested loop: for each kept result, re-tokenize signature. At `limit=10` with `raw_limit=20`, that's up to 200 tokenize calls per query. Trivially micro-optimizable: tokenize once, pass token sets. Probably 1ms savings. Defer.

**[P3] (confidence: 9/10) `model.encode()` loads the transformer on every `wiki_search.py --mode semantic` invocation.**

`_MODEL_CACHE` in `semantic.py:58` only helps within a single Python process. Each CLI call reloads ~90MB + warm-up time. If QUERY is a one-shot Python call per question, that's ~3 seconds of model load per query.

**Recommendation:** Accept as-is (that's the cost of shelling out). If it becomes painful, run a small daemon (`scripts/search_daemon.py`) with a unix socket. Defer until the cost is felt.

---

## NOT in scope

Things I considered and excluded from this review:

- **CLAUDE.md prose correctness.** The spec is thorough; I reviewed the code's implementation of it, not the spec itself.
- **Template design.** `templates/*.md` not read. Separate concern.
- **The markitdown ingestion pipeline.** CLAUDE.md:281-313 — depends on an external tool; quality depends on markitdown, not z-wiki.
- **Obsidian plugin config.** `.obsidian/` is user-owned.
- **`.claude/skills/` and `.claude/commands/`.** Vendored and user-configured; out of scope for a system review.

## What already exists

Everything this review evaluates is already built. No rebuild recommended. Two items to add:

1. Regression test for the `np.save` bug (mandatory).
2. GitHub Action running `check_invariants.sh` (high-value, 20 lines).

Everything else is polish — fix when you're editing nearby code, not as a standalone task.

---

## Failure modes (production-realistic)

| Failure mode | Covered? | Blast radius |
|---|---|---|
| Slug collision between two sources | [GAP] — silent last-write-wins in `build_meta.py`, caught only by `test-unique-slugs.sh` after the fact | Corrupted backlinks; stale index until next LINT |
| User hand-edits `wiki/.meta/` | Partially — `--check` detects some drift but invariants don't police `.meta/` directly | Next rebuild overwrites; low harm |
| `markitdown` produces gibberish on a scanned PDF | Prose-specified fallback (CLAUDE.md:298) to rasterize | User visible; Claude decides |
| Embedding model download fails mid-INGEST | `_import_st()` raises; `build_meta.py --embed-if-enabled` warns and continues without embeddings | Degrades to lexical; acceptable |
| Concurrent `build_meta.py` runs | [GAP] — atomic writes protect the file, but two runs racing on `.tmp` paths could collide | Rare (single-user), but would silently swap partial data |
| `embeddings.npy` maliciously crafted | [GAP] — `np.load` default permits arbitrary-object deserialization | Arbitrary code execution if someone PRs a poisoned `.npy` |
| Frontmatter has a nested dict a future template adds | [GAP] — hand-rolled parser drops it silently | Data loss on that field |

**Critical gaps** (no test AND no error handling AND would be silent):
1. Slug collision silent overwrite.
2. `np.load` default permits arbitrary-object deserialization.
3. Nested-dict frontmatter silent drop.

The first two are 1-3 line fixes. The third is either "add invariant test" or "switch to PyYAML."

---

## Parallelization (for follow-up work)

| Step | Modules touched | Depends on |
|---|---|---|
| 1. Regression test for np.save bug | `tests/` | — |
| 2. `allow_pickle=False` in both loaders | `scripts/` | — |
| 3. Slug collision detection | `scripts/build_meta.py` + `tests/` | — |
| 4. GitHub Action for invariants | `.github/workflows/` | — |
| 5. `inbound_refs_primary` scoping | `scripts/build_meta.py` + CLAUDE.md | 3 (same file) |

Lanes: 1, 2, 4 are independent (A, B, C parallel). 3 → 5 sequential (same file). Pragmatic order for one person: land 1 + 2 + 4 together (small, safe), then 3, then 5.

---

## Completion summary

- **Step 0 (scope):** Reviewed architecture + code + tests + performance. No scope reduction needed — single-file fixes and one regression test.
- **Architecture:** 5 issues found (1 P1, 3 P2, 1 P3).
- **Code quality:** 6 issues found (1 P1 security, 3 P2, 2 P3).
- **Tests:** 1 P1 regression (mandatory), 2 P2 unit-coverage gaps, 1 P3 eval suggestion.
- **Performance:** 4 issues found — all deferrable until vault > 500 sources.
- **NOT in scope:** written.
- **What already exists:** written.
- **Failure modes:** 3 critical gaps flagged (slug collision, unsafe `np.load` default, nested YAML).

**VERDICT:** Architecture is sound. Ship the np.save regression test + `allow_pickle=False` + slug collision detection this week. Everything else is polish. The system is well-designed for its scale target and currently over-instrumented for its load (0 sources) — that's fine, because the complexity is real once you hit 100+ sources, and retrofitting it then would be harder than building it now. Write more sources.

**One concrete thing to do next:** add `tests/test-embeddings-tmp-path.sh` from the snippet above before the bug rots out of memory. It's the shortest path to making your fix stick.
