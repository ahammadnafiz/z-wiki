---
description: Process new files in raw/ into wiki pages.
argument-hint: "[path]"
when_to_use: Run after dropping sources into raw/articles/, raw/papers/, or raw/transcripts/. Without arguments, processes every unprocessed source; with a path, ingests only that file. Also triggered by phrases like "ingest the new source", "process raw", "compile what I dropped in".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Wiki Ingest

Read `CLAUDE.md` for conventions. Follow the INGEST operation exactly as specified there.

## Scope
- If `$ARGUMENTS` is empty: find every `raw/**/*.{md,pdf,txt}` that has no matching `wiki/sources/{slug}.md`.
- If `$ARGUMENTS` names a path under `raw/`: ingest only that file.

## Before writing anything
- Confirm each source's counterpart does not already exist. If it does, skip.
- Read each source fully before drafting. PDFs: read directly; if scanned, rasterize and read visually.
- If a PDF is > ~50 pages, stop and propose a chapter-split plan before ingesting any of it.
- No skimming.

## During ingest
- Pick the right template per `CLAUDE.md` → INGEST step 2b: `paper-summary.md` for anything in `raw/papers/`, `source-summary.md` otherwise.
- Every new page must have complete frontmatter per the schema in `CLAUDE.md`.
- Every `[[wikilink]]` must resolve by the time you finish the ingest — create stubs from `templates/stub.md` for any concept/entity that would otherwise dangle.
- Promote stubs to full pages in-place when this ingest pushes their `source_count` to ≥2 (see CLAUDE.md → INGEST step 2c).
- Flag contradictions inline with `> [!warning] Contradiction` callouts.
- Append-only to `wiki/log.md`. One entry per source ingested.
- Regenerate `wiki/index.md` from the filesystem at the end (not incrementally).

## Reporting
At the end, print a summary:
- Sources ingested (list)
- Concept/entity pages created (list)
- Stubs created (list)
- Pages updated in place (list)
- Contradictions flagged (list with file paths)
- Files you refused to ingest and why (list)
