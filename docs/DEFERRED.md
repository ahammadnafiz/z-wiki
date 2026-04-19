# Deferred work

Things we deliberately haven't built. Each item has a trigger
condition — a vault size or symptom that would justify revisiting.

## Tier 2 — when scale warrants it

### Batched markitdown extraction (Eng Review §4B, 4D)

**Status:** deferred.

**Current behavior:** `markitdown` is invoked once per source via a
subprocess. Each call has ~200–500 ms of startup overhead; at 50
sources this is ~15–25 seconds of pure process startup before any
LLM work happens.

**Fix when needed:** run extractions in parallel inside each
subagent:

```bash
find raw/papers -name '*.pdf' -print0 |
  xargs -0 -P 4 -I{} sh -c 'markitdown "$1" -o "/tmp/$(basename "$1").md"' _ {}
```

`-P 4` caps parallelism so we don't thrash the CPU. The
per-subagent INGEST flow stays sequential once extractions are
done (summarization is LLM-bound, not CPU-bound).

**Trigger:** >30 sources in a single batch, or any complaint that
"ingest is slow before Claude even starts reading."

### Automated chapter splitter for >200K-token books (Eng Review §4E)

**Status:** manual for now. INGEST prompts the user to propose a
split plan.

**Why deferred:** accurate chapter detection requires reading the
PDF table of contents. PDFs don't have a standard TOC format; the
current "stop and propose" rule puts the judgment on the human,
which is correct for a 500-page book where we're committing to 10
separate source summaries.

**Fix when needed:** `scripts/split_book.py` that uses PyMuPDF
(`fitz`) to read the PDF outline and emit a proposed slug-per-chapter
mapping. Adds PyMuPDF as an optional dep (~20MB). Only worth
building if the user ingests >3 books total.

**Trigger:** three or more books have gone through the manual flow
and the slug-proposal step felt tedious.

### Operation-semantics fixture suite (Eng Review §3)

**Status:** one test shipped (`tests/test-ingest-idempotent.sh`).

**Other scenarios not yet covered:**
- INGEST of the same source twice produces no duplicate summary.
  (Partial coverage today via the idempotency test on sidecar
  detection, but no end-to-end test of the INGEST LLM flow itself.)
- Contradiction callout survives re-ingest.
- Stub promoted to full page preserves pre-promotion summary +
  source backlinks.
- LINT auto-fix converges (one run fixes everything fixable; second
  run is a no-op).

**Why deferred:** each of these needs a scripted LLM round-trip
against Anthropic — genuine LLM tests, not pure logic tests. Cost
per run is modest but nonzero. Worth building when we have real
sources in the vault to test against, not synthetic fixtures.

**Trigger:** vault has >20 real sources AND a production-style
regression makes us regret not having the test.

## Tier 3 — might never be worth it

### Template consolidation (Eng Review §2F)

**Status:** `paper-summary.md` and `source-summary.md` remain
separate.

**Considered:** merging into `templates/source-base.md` +
type-specific overlays.

**Why not doing it:** the two templates genuinely differ — papers
carry bibliographic fields (DOI, arxiv, page_count, venue) that
articles don't have. Merging forces every source to carry empty
bibliographic fields, which is worse. The duplication we'd remove
is maybe 10 lines of YAML boilerplate across two files. Not worth
the abstraction cost.

**Would reconsider if:** we add 3+ more source types (transcript,
voice-memo, email), and the per-type duplication grows.

### Last-seen batched ledger (Eng Review §2D)

**Status:** `last_seen` writes into page frontmatter directly.

**Considered:** batching updates into a sidecar
`wiki/.meta/last_seen.json`, flushing into frontmatter only during
LINT.

**Why not doing it:** frontmatter writes are cheap. Git diff noise
is real but tolerable at personal-vault scale. The sidecar approach
adds state that can drift from frontmatter — one more thing for
LINT to reconcile.

**Would reconsider if:** git diffs become actively annoying (more
than ~50 frontmatter-only touches per commit) or git operations
feel slow.

### SessionStart hook for unprocessed-raw notifications

**Status:** considered and explicitly declined by the user.

**Rationale:** the user prefers explicit `/wiki-ingest` over a
SessionStart banner that nudges every time. Valid — the banner is
noise until you have the intent. Revisit only if the user asks.

## Tier 1 — done in this pass

For the record:
- Citation-resolve invariant (`tests/test-outputs-citations-resolve.sh`)
- Gibberish extraction detector (`scripts/check_extraction.py`)
- Tightened recursive chunking spec (CLAUDE.md INGEST §2a)
- Ingest-idempotent test (`tests/test-ingest-idempotent.sh`)
