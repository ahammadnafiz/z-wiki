---
name: context-engineering
description: How to manage Claude's context window while running z-wiki operations. Covers subagent dispatch, /rewind vs /compact vs /clear, prompt-cache structure, and staleness-aware reads. Read this before running INGEST on big batches, LINT across many pages, or QUERY on a large vault.
---

# Context engineering — z-wiki

The 1M context window is double-edged: it lets one session handle a
whole ingest batch, but attention degrades as context grows ("context
rot," usually felt around 300–400K tokens depending on task). The
commands in this repo are designed to keep you well under that ceiling.

Use this skill whenever:

- You are about to ingest more than ~5 sources at once.
- You are about to run `/wiki-lint` on a vault with more than ~500
  pages.
- You are mid-session and sensing confusion or repetitive re-reads.
- You need to decide between continuing, rewinding, compacting,
  clearing, or spawning a subagent.

## The five moves

After a turn finishes you always have five options. They are *not*
interchangeable. Pick by intent.

| Move | When | z-wiki example |
|---|---|---|
| **Continue** | Next step is on the same task and needs what you just learned. | You just extracted concepts from source A; now file the summary. |
| **/rewind** (double-Esc) | Something went wrong and you want to re-prompt from a clean state. | INGEST picked the wrong template; rewind to before the template read and redirect. |
| **/compact** | Session is long but the task direction is predictable. | Mid-batch ingest with 10 more sources of the same type to go. |
| **/clear** with handoff brief | Starting a related but distinct task. | Just finished INGEST; about to run QUERY on the new vault. Clear, then prompt with "vault now has sources X, Y, Z — answer: ..." |
| **Subagent** | Next chunk produces intermediate output you will not need again. | Running `/wiki-lint`'s cross-page contradiction sweep; only the report matters. |

## When each move is the *right* move in z-wiki

### `/rewind` beats "try again" for botched ingests

If `/wiki-ingest` read a source and went down a wrong path (misclassified
a paper as an article, used the wrong template, created a bad concept
stub), double-tap Esc to rewind to just before the mistake and re-prompt
with the correction. Do **not** type "that was wrong, try again" — that
leaves the bad reasoning in context and biases the next attempt.

Concretely: rewind to just after the raw-source was read, then re-prompt:
> Treat this as a `paper`, not an `article`. Use `templates/paper-summary.md`.
> The paper has 12 sections; summarise at section granularity.

### Subagents are the INGEST scaling lever

INGEST of a single source reads the raw file (potentially 50K+ tokens),
extracts concepts, creates wiki pages, and writes summaries. Most of
that raw-file content is intermediate — only the **summary + the set of
concept slugs created** matters to the parent session.

**Rule of thumb:** when ingesting a batch of 3+ sources, dispatch one
subagent per source. The subagent returns a structured report:

```
SOURCE: <slug>
SUMMARY PATH: wiki/sources/<slug>.md
CONCEPTS CREATED: [slug1, slug2, slug3]
STUBS CREATED: [slug4, slug5]
CONTRADICTIONS: [one-line each, with file path]
```

The parent session never sees the raw PDF content. Parent's context
stays thin; batch scales to 20+ sources without hitting context rot.

### Compaction is dangerous mid-INGEST

Autocompact during INGEST is the worst-case scenario: the wikilink
ledger (what stubs to create, what cross-refs to resolve at end of
pass) is precisely the "unpredictable direction" content the
compactor is bad at preserving. If autocompact fires mid-ingest, the
ledger can be summarised away and stubs created as dangling links.

**Mitigations:**
1. For any batch of >5 sources, use subagents (above). Parent context
   never grows enough to trigger autocompact.
2. If you *must* ingest in one context, run `/wiki-compile` and
   `/wiki-lint` immediately after. Lint will catch dangling links.
3. Never run `/compact` *manually* inside `/wiki-ingest`. If you are
   sensing context pressure, `/clear` + handoff brief is safer.

### `/clear` with a handoff brief after each operation

After a completed operation (one INGEST batch, one QUERY, one LINT),
the conversation context is typically no longer useful. Clear it and
open a new session with a one-screen handoff:

> Vault state: 47 sources, 183 concepts, 41 entities. Last session
> ingested Karpathy's LLM-KBs post; created concepts `[[llm-knowledge-base]]`,
> `[[wiki-compile-loop]]`; promoted stub `[[knowledge-base-design]]`. Next:
> ingest the three papers in `raw/papers/` from today's drop.

The handoff is cheaper than the full conversation and more accurate
than a compacted summary.

## Prompt-cache structure

The repo is set up so `CLAUDE.md` (293 lines, stable) can benefit from
Anthropic prompt caching. The cache has a 5-minute TTL, so any
session that runs several operations back-to-back gets the cached
prompt for free on the 2nd+ operation.

**Two rules to keep the cache effective:**

1. **Read stable content first, mutable content last.** `CLAUDE.md` is
   stable across the whole session — always read it before
   `wiki/index.md`. Reading the mutable file first would invalidate
   the cache because Anthropic caches a contiguous prefix.
2. **Avoid mid-operation edits to files you've already read.** If
   `/wiki-ingest` is mid-pass and you need to consult `CLAUDE.md`
   again, Claude should re-reference its in-context copy, not re-read
   from disk. Re-reading after a write anywhere breaks cache.

The commands are written so this happens naturally — but if you are
composing a custom operation, keep the order: `CLAUDE.md` → skill
references → `wiki/index.md` → candidate pages → output write.

## Grep-first is context-first

The biggest context win in z-wiki is **not loading `wiki/index.md` on
every QUERY.** At 2000 sources, that is ~40K tokens of context eaten
before reading a single page.

The designed flow is:

1. Grep (`python3 scripts/wiki_search.py <query>`) → returns ranked
   path list, costs zero Claude context beyond the returned paths.
2. Read the top N candidate pages directly.
3. Consult `wiki/indexes/by-tag/<tag>.md` only if the query is
   tag-scoped and grep missed.
4. Fall back to `wiki/<type>/_index.md` only if tag shard insufficient.
5. `wiki/index.md` itself — the top nav — is small by construction
   (<1K tokens) and rarely needed mid-query.

Same principle for INGEST: **consult `wiki/.meta/backlinks.json`** to
check if a stub already exists, not by reading every concept file.

## Staleness gates

`last_seen` in frontmatter marks the last time any operation actually
**read** a page in service of a task. The LINT staleness gate uses
this to skip pages read recently.

Concrete rules:
- A page with `last_seen` set by an operation in the last 7 days does
  not need a full-body re-read during `/wiki-lint`. Frontmatter scan
  only.
- A page's `last_seen` should **not** be bumped just because INGEST
  resolved a `[[wikilink]]` to it — only if INGEST substantively read
  the body (e.g. to check for contradictions, to append a new
  reference). Guards against write amplification.

## When context feels wrong

Signs you should stop and reset:

- Claude re-reads the same file twice in a single operation (context
  rot; attention lost the first read).
- Claude proposes to create a file that already exists (the parent's
  ledger fell out of attention — a subagent would have been better).
- The user's last message seems to have been interpreted through a
  filter from two turns ago (bad compaction).
- The running summary of "what we've done" doesn't match what
  actually got written to disk (you're in a hallucinated branch;
  `/rewind` is the fix).

When you see these: stop, acknowledge, and offer `/clear` with a
handoff brief rather than pushing through.

## References

- The operating principles here are the Anthropic Claude Code team's
  public guidance on context management (1M context, context rot,
  /rewind vs /compact, subagent use). The z-wiki-specific
  applications are the value add of this skill.
