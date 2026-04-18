---
description: Print current vault stats — sources, concepts, entities, stubs, recent activity.
when_to_use: Use for a quick read on where the vault stands. Read-only; writes nothing. Triggered by phrases like "status", "vault stats", "what's in the wiki", "how many sources".
allowed-tools: Read, Bash, Glob, Grep
---

# Wiki Status

Print a one-screen summary of the current vault. Read-only — never writes.

## What to report

### Counts

| Layer | Count |
|---|---|
| Sources (`wiki/sources/`) | N |
| Concepts (full pages) | N |
| Concepts (stubs) | N |
| Entities (full pages) | N |
| Entities (stubs) | N |
| Syntheses | N |
| Outputs | N |

Exclude `_index.md` files from counts.

### Health signals

- **Raw sources awaiting ingest** — collect the set of `source_path:` values from every `wiki/sources/*.md` frontmatter; compare against all `raw/**/*.{md,pdf,txt}` paths. Any raw file whose path is not in that set is unprocessed. Report the count; if >0, list the paths. **Do not** detect by filename match — raw filenames intentionally differ from wiki-summary slugs.
- **Stubs approaching promotion** — list stubs whose `source_count ≥ 2` OR whose estimated `inbound_refs ≥ 5` (use grep to estimate). These are what `/wiki-lint` would promote next.
- **Recent activity** — last 5 entries from `wiki/log.md` (just the header lines).

### Size

- `wiki/index.md` — lines and approximate token count (chars ÷ 4). Flag if approaching the graduation threshold (500 lines or 10K tokens).
- Total `wiki/` content size (du -sh).

## Format

Tight single-screen output. Use tables for counts, bullet lists for everything else. No prose paragraphs.

## Guardrails

- Do not write to any file. No `wiki/outputs/status-*.md`. No index or log updates.
- Do not invoke other commands. No auto-ingest, no auto-lint.
- If the vault is empty (0 sources), say so with a one-liner pointing the user at `/wiki-init` or `/wiki-add`.
