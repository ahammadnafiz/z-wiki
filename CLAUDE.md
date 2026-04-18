# z-wiki — Schema and Operating Spec

## Overview
<!-- REPLACE THIS LINE with a one-paragraph description of YOUR knowledge base's topic. Be specific: what domains? What's in scope, what's not? This anchors every ingest — without it, Claude has no signal for what to emphasise or skip. Example: "Personal knowledge base on urban planning and housing policy, with emphasis on North American case studies from 1960–2025." -->

You (Claude) are the maintainer. The user curates sources and asks questions. You execute
ingest, compile, query, and lint. Raw sources are immutable. The wiki is yours
to write and revise. The user rarely edits wiki pages by hand.

## Layers
- `raw/` — source material. Read-only for you. Subfolders: `articles/`, `papers/`,
  `transcripts/`, `assets/` (images, PDFs, binaries referenced by sources).
- `wiki/` — your working output. See structure below.
- `templates/` — reference templates. Copy the relevant template when creating
  a new page; do not deviate from the frontmatter schema.

## Wiki structure
- `wiki/index.md` — master index. Sectioned by type. You regenerate it on every
  ingest, query, and lint. Plain markdown only — no Dataview, no embedded queries.
- `wiki/log.md` — append-only changelog. Never rewrite, only append. Each entry
  starts with `## [YYYY-MM-DD HH:MM] <op> | <short-title>`.
- `wiki/sources/` — one summary per raw source. Filename: `{slug}.md` derived
  from the raw filename.
- `wiki/concepts/` — one page per concept. Full page if ≥2 sources mention it;
  stub otherwise.
- `wiki/entities/` — one page per person, organisation, library, project, tool.
  Same threshold.
- `wiki/outputs/` — filed answers to my queries and lint reports. QUERY **always**
  writes here; never directly to `syntheses/`.
- `wiki/syntheses/` — cross-cutting analyses. Created **only** when I explicitly
  ask, or when a stable thread of outputs is promoted (crystallized) into a
  synthesis. Syntheses are promoted outputs, not auto-generated from a single query.
- `wiki/attachments/images/` — charts, diagrams, anything you generate (figures
  extracted from sources land here; see Quality bar).
- `wiki/views/` — Obsidian Bases (`.base` files). **Ornamental.** Dynamic
  views over frontmatter (tables, cards, list, map). Must not become primary
  navigation. Syntax: `.claude/skills/obsidian-bases/SKILL.md`.
- `wiki/canvases/` — Obsidian JSON Canvas (`.canvas` files). **Ornamental.**
  Visual workspaces for mind-maps, architectural diagrams, dependency graphs.
  Any knowledge expressed in a canvas must also exist in plain markdown
  somewhere in `wiki/`. Syntax: `.claude/skills/json-canvas/SKILL.md`.

## File conventions
- Filenames: lowercase, kebab-case, ASCII only. No spaces, no underscores, no
  uppercase. `active-inference.md`, not `Active_Inference.md`.
- Source summaries: `{author-lastname}-{year}-{short-title}.md` when author/year
  are known; otherwise `{publisher}-{short-title}.md`.
- All files must have YAML frontmatter matching the schema below.
- Links: `[[shortest-path]]` style. Obsidian resolves by filename because
  filenames are globally unique in this vault — enforce that invariant when
  creating pages. If a name would collide, disambiguate with a suffix
  (`uniswap-protocol.md` vs `uniswap-labs.md`).
- Bold key terms on first use per article. Link first occurrence per section.

## Frontmatter schema (all wiki pages)
```yaml
---
title: "Page Title"
type: source | concept | entity | synthesis | output | stub
status: draft | review | final
date_created: YYYY-MM-DD
date_modified: YYYY-MM-DD
last_seen: YYYY-MM-DD
summary: "One to two sentences. No line breaks."
tags:
  - domain-tag
  - topic-tag
---
```
- `last_seen` — the date any operation (INGEST, QUERY, LINT) last
  substantively read, cited, or wrote this page. Distinct from `date_modified`,
  which tracks body edits only. Used by LINT to surface stale content.

Additional fields by type:
- `source`: `source_url`, `source_path` (relative to vault root), `authors`, `published`, `source_type`. Papers add `venue`, `doi`, `arxiv`, `page_count`.
- `concept` / `entity`: `related` (list of `[[wikilinks]]`), `source_count` (int, **derived** — the number of distinct `wiki/sources/*.md` files that wikilink to this page. Canonically recomputed by COMPILE and LINT; never hand-edited).
- `output`: `question`, `answered_on` (YYYY-MM-DD), `sources_cited`.
- `stub`: `promote_when` — short note on what would justify promoting to full page.

## Operations

### INGEST
Trigger: I say "ingest" or run `/wiki-ingest`, or you see new files in `raw/`
that have no matching summary in `wiki/sources/`.
Steps:
1. Find unprocessed sources: files in `raw/**/*.{md,pdf,txt}` with no
   `wiki/sources/{slug}.md` counterpart.
2. For each one:
   a. Read fully.
      - Markdown / text: read directly.
      - PDF: read the file directly (Claude Code supports native PDF input).
        If text extraction is poor (scanned / image-only PDF), rasterize
        pages and read visually.
      - PDF > ~50 pages (books, theses, long reports): **stop before writing
        anything** and propose a chapter-split plan — one source summary per
        chapter or per logical unit, slug suffixed `-ch01`, `-ch02`, etc.
        Wait for my go-ahead before ingesting.
      - Standalone image without a companion markdown/PDF: tell me and stop.
        Images alone are not a source.
   b. Create `wiki/sources/{slug}.md` from the right template:
      - `templates/paper-summary.md` for anything in `raw/papers/` (academic
        papers, book chapters, long-form PDFs with citations).
      - `templates/source-summary.md` for articles, transcripts, and
        everything else.
   c. Extract concepts and entities. For each:
      - **Does not exist** → create a stub from `templates/stub.md`. Every
        `[[wikilink]]` you write must resolve by end of ingest — no dangling
        links permitted.
      - **Exists as a stub** → append this source to its backlinks. Inline
        promotion (rewrite as a full page) happens in step 3's whole-vault
        sweep below, which sees the page's full post-ingest state. This
        avoids the previous failure mode where a stub crossed the threshold
        via *another* source's later citation and never got promoted,
        because no single ingest saw the new total.
      - **Exists as a full page** → append new information. Never rewrite
        prose that hasn't changed.
   d. Contradictions: when new information conflicts with an existing page,
      insert a `> [!warning] Contradiction` callout at the point of conflict
      citing both sources. Never silently reconcile. See the canonical rule
      below.
3. **Whole-vault post-pass** (runs once after all sources in step 2 are
   processed):
   a. Recompute `source_count` for every concept/entity page (distinct
      `wiki/sources/*.md` files wikilinking to it) and `inbound_refs`
      (distinct pages wikilinking to it). Update frontmatter where drifted.
   b. Promote any stub whose recomputed values meet either threshold in
      "Page creation thresholds." Rewrite using `templates/concept.md` or
      `templates/entity.md`, preserving existing summary and source
      backlinks. Promotion is shared between INGEST (this step) and LINT.
   c. Set `last_seen: YYYY-MM-DD` on every page this ingest touched:
      the new source summary, every stub created, every stub promoted,
      every full page appended.
4. Regenerate `wiki/index.md` from scratch (sectioned by type, plain markdown).
5. Append one entry per source to `wiki/log.md`.
6. Report: sources processed, pages created, pages updated, stubs created,
   stubs promoted, contradictions flagged.

### QUERY
Trigger: `/wiki-query <question>` or I ask a question in chat.
Steps:
1. Read `wiki/index.md`.
2. Identify candidate pages from the index. Read them.
3. If coverage is insufficient, tell me which raw sources I should add — do
   not invent facts.
4. Synthesize an answer. Cite every non-obvious claim with a `[[wikilink]]`
   to a source summary or concept page.
5. Save to `wiki/outputs/{question-slug}.md` using `templates/output.md`.
6. Set `last_seen: YYYY-MM-DD` on the new output page and on every page
   cited in the answer. This is how the wiki records "the agent actually
   read and used this page today," distinct from `date_modified`.
7. Update `wiki/index.md` and `wiki/log.md`.

### LINT
Trigger: `/wiki-lint` or weekly.
Steps:
1. Scan every file in `wiki/`.
2. Find and fix automatically:
   - Missing/malformed frontmatter (including missing `last_seen`; initialize
     to `date_modified` if absent).
   - Broken wikilinks (create stubs).
   - Inconsistent filenames (rename + update refs).
   - Duplicate pages under different names (merge).
   - **Drifted `source_count`** — recompute canonically from inbound
     `wiki/sources/*.md` wikilinks; rewrite any stale values.
   - **Stubs that meet either promotion threshold** (see "Page creation
     thresholds") — rewrite as full pages using the appropriate template,
     preserving existing summary and source backlinks. LINT has explicit
     promotion authority; it shares this responsibility with INGEST.
3. Find and report (do not auto-fix):
   - Contradictions between pages (cross-page sweep; insert `> [!warning]`
     callouts plus a list in the report).
   - Orphan pages (no inbound wikilinks).
   - Stale content: `last_seen` older than 180 days. Do **not** use the
     source's `published` date — foundational papers are not "stale" simply
     because they are old.
   - **Synthesis candidates:** any cluster of ≥3 outputs sharing ≥2 cited
     pages. Propose a synthesis topic in the report and list the outputs;
     I decide whether to promote.
4. Set `last_seen` on every page LINT substantively edited in step 2.
5. Write `wiki/outputs/lint-report-{today}.md`. Update index and log.

### COMPILE
Trigger: `/wiki-compile` when you suspect index drift.
Steps:
1. Recompute `source_count` for every concept/entity page from inbound
   `wiki/sources/*.md` wikilinks. Rewrite frontmatter where drifted. This
   is the one frontmatter field COMPILE is allowed to touch; body content
   is never modified.
2. Rebuild `wiki/index.md` from the file system.
3. Append a `compile` entry to `wiki/log.md`.

## Page creation thresholds
A stub graduates to a full page when **either** axis is met:

- **Source axis:** `source_count ≥ 2` — the subject appears in ≥2 raw
  sources (i.e. is wikilinked from ≥2 distinct `wiki/sources/*.md` pages).
- **Reference axis:** `inbound_refs ≥ 5` — the subject is wikilinked from
  ≥5 distinct pages anywhere in `wiki/`. Catches concepts that are
  load-bearing inside one deep source or structurally central to the vault
  even when only one source has covered them so far.

Both axes are evaluated by the Ingest post-pass (step 3) and by Lint.

- Stub: subject appears in exactly 1 raw source but is referenced by a
  `[[wikilink]]`. Must include frontmatter + one-sentence definition + link
  back to the source that mentioned it.
- Never: leave a `[[wikilink]]` pointing to nothing.

## Contradictions (canonical)
Ingest flags contradictions it encounters **while touching pages in this
ingest** (inline `> [!warning] Contradiction` callout, cites both sides).
Lint does the **cross-page sweep** across the entire wiki and issues fresh
callouts for any it finds plus a list in the lint report. Neither operation
resolves a contradiction silently — resolution is my call.

## Quality bar
- Source summaries (articles, transcripts): 200–500 words, synthesis not
  transcription.
- Paper summaries: 300–800 words; **must** include bibliographic frontmatter
  and inline page citations on quotes and specific claims: `(p. 7)` or
  `(pp. 7–9)`.
- Concept / entity pages: 300–1200 words once promoted; 1 line for stubs.
- Every claim traceable to a specific source page.
- Figures: describe in prose by default. Extract to
  `wiki/attachments/images/` only when I explicitly ask, or when the figure's
  structure genuinely can't be captured in words (e.g. novel diagrams).
- Equations: use Obsidian's native MathJax. Inline math: `$...$`. Display
  (block) math: `$$...$$` on its own lines. **Do NOT wrap math in backticks** —
  backticks render as inline code (monospace), not typeset math. Use math
  mode for symbols and expressions ($d_{\text{model}}$, $QK^\top$,
  $\sqrt{d_k}$, $O(n)$, $10^{89}$, $E = mc^2$, etc.), not for programming
  constants or CLI strings (those stay in backticks). When an equation is
  nontrivial, follow it with a plain-language summary of what it's saying.
- When sources conflict, prefer recency, but flag with ⚠️ and preserve both.
- Avoid prose that could apply to any topic. If a paragraph would read the
  same for a different concept, rewrite it.

## Skill references

Agent Skills are vendored under `.claude/skills/`. **Primary integration:** read the relevant `SKILL.md` with the `Read` tool when you need its syntax — the table below tells you when. Do not duplicate the content here.

Claude Code may also auto-discover these for native `Skill`-tool invocation in fresh sessions (project-scoped skills spec is `.claude/skills/<name>/SKILL.md`). Before relying on that path, confirm the five skill names (`obsidian-markdown`, `obsidian-bases`, `json-canvas`, `obsidian-cli`, `defuddle`) appear in the session's available-skills list. If they don't, fall back to the Read path — the skill content is identical.

| Skill | When to consult |
|---|---|
| `.claude/skills/obsidian-markdown/SKILL.md` | Wikilinks, callouts, embeds, tags, properties, highlights (`==...==`), comments (`%%...%%`), inline/block math, Mermaid, footnotes. |
| `.claude/skills/obsidian-bases/SKILL.md` | Writing `.base` files for `wiki/views/`. Filters, formulas, view types, YAML quoting rules, common errors. |
| `.claude/skills/json-canvas/SKILL.md` | Writing `.canvas` files for `wiki/canvases/`. Node/edge schema, ID generation, layout guidelines. |
| `.claude/skills/obsidian-cli/SKILL.md` | Driving a running Obsidian instance from the shell (read/create/search/tasks/backlinks). Check `obsidian` is on PATH first; skill is a no-op if the CLI isn't installed. |
| `.claude/skills/defuddle/SKILL.md` | Extracting clean markdown from standard web pages. **Prefer `defuddle` over `WebFetch` for article-style URLs**; WebFetch remains correct for arXiv HTML, GitHub, raw `.md` URLs, and anything already structured. Check `defuddle` is on PATH first; falls back to WebFetch if not installed. |

## Things you must not do
- Modify anything in `raw/`.
- Rewrite `wiki/log.md`.
- Use Dataview, Canvas, or Bases as **load-bearing** structure. The
  authoritative index (`wiki/index.md`), changelog (`wiki/log.md`), every
  `_index.md`, and every source / concept / entity / synthesis / output page
  stays plain markdown + YAML + `[[wikilinks]]`, because it must render on
  GitHub and be readable by any tool. Bases live only in `wiki/views/` and
  Canvas files only in `wiki/canvases/`, and both are ornamental.
- Put a `.base` view where a plain-markdown index would do, or a `.canvas`
  where prose would do. Ornamentation is earned by "prose can't capture
  this," not by "it's prettier."
- Create files outside the structure listed in "Wiki structure".
- Leave broken wikilinks. Leave missing frontmatter. Skip the log entry.
- Edit `.obsidian/` or `.claude/` unless I explicitly ask. (Exception:
  vendoring / updating `.claude/skills/` is an explicit operation I drive.)
- Delete pages. If a page should go, mark `status: deprecated` in frontmatter
  and tell me.
