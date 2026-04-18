# z-wiki — User Guide

> This is the step-by-step guide for using z-wiki. Written for future-you in three months when you've forgotten how this works, and for anyone else you share the repo with. If you only want a 30-second overview, read `README.md` instead and come back here when something breaks.

---

## 1. What z-wiki is, in one minute

z-wiki is a personal LLM-maintained knowledge wiki built around **three layers** you should hold in your head at all times:

| Layer | What's in it | Who owns it |
|---|---|---|
| `raw/` | Source material you drop in (articles, papers, transcripts) | **You** — immutable once placed |
| `wiki/` | LLM-authored pages (summaries, concepts, entities, syntheses, outputs, lint reports) | **Claude Code** |
| `CLAUDE.md` | The spec that tells Claude how to write and maintain `wiki/` | **Both of you** — co-evolved |

The pattern runs on **four operations that cycle continuously**:

1. **Ingest** — you drop a source; Claude writes a summary and updates concept/entity pages
2. **Query** — you ask a question; Claude searches the wiki and files the answer back
3. **Lint** — Claude audits the wiki for broken links, orphans, drift
4. **Compile** — Claude regenerates `wiki/index.md` from the current state

The **filing loop** is the point: every answer becomes new wiki content that future answers can cite. Knowledge compounds.

Tools involved:
- **Claude Code** — reads/writes files, executes the operations above
- **Obsidian** — the reading surface; renders wikilinks, graph, math, Bases, Canvas
- **Git** — version history; every commit is a snapshot of the wiki's state

---

## 2. Prerequisites

| Tool | Version | Why |
|---|---|---|
| [Obsidian](https://obsidian.md) | ≥1.4 | Vault UI, MathJax, Properties pane |
| [Claude Code](https://claude.ai/download) | any recent | Runs ingest/query/lint/compile |
| `git` | any | History; nothing works without it |
| `defuddle` | any (optional) | `npm install -g defuddle` — clean web-page extraction; falls back to WebFetch if absent |
| `obsidian` CLI | any (optional) | `obsidian help`; drives a running Obsidian from the shell |

macOS / Linux paths are assumed. Windows should work via WSL.

---

## 3. First-time setup

### 3.1 Getting the vault on a new machine

If cloning from git:

```bash
git clone <your-repo-url> z-wiki
cd z-wiki
```

If starting fresh, you've already cloned the template; skip to the next step.

### 3.2 Open the folder as an Obsidian vault

In Obsidian: **File → Open folder as vault** → pick the `z-wiki/` directory. Obsidian creates or reads `.obsidian/` with the pre-configured settings:

- `newLinkFormat: "shortest"` — `[[concept-name]]` resolves by filename
- `attachmentFolderPath: "raw/assets"` — pasted images land with the raw sources
- `newFileFolderPath: "raw/articles"` — new notes default to the inbox
- `strictLineBreaks: false` — Obsidian and GitHub render the same
- `userIgnoreFilters` excludes `CLAUDE.md`, `README.md`, `docs/` from graph and default search

Sanity check in Obsidian:

1. Graph view (Cmd-G) — should render without errors (empty is fine; you have no content yet).
2. Open `wiki/index.md` — Properties pane (right sidebar) should show typed fields (title, type, tags), **not** raw YAML text. If you see raw YAML, enable the Properties core plugin in Obsidian settings.
3. Math rendering — after you ingest a source with equations (or type `$E = mc^2$` in any note), math should render typeset, not as `$...$` literal text. If not, enable LaTeX/MathJax in Obsidian settings → Editor.

If any of these fail, see [Troubleshooting](#12-troubleshooting).

### 3.3 Start a Claude Code session

In a terminal inside the vault:

```bash
cd /path/to/z-wiki
claude
```

The session header should mention `CLAUDE.md` was loaded. Verify by asking: *"What operations are defined in CLAUDE.md?"* — the answer should mention INGEST, QUERY, LINT, COMPILE.

### 3.4 Fill in the vault's topic

Run `/wiki-init`. On a fresh clone this triggers an interactive wizard: Claude asks about your topic conversationally and writes your answer into `CLAUDE.md` → Overview (replacing the `<!-- REPLACE THIS LINE -->` placeholder). On every subsequent run, the wizard is skipped and only directory/template verification happens.

Why this matters: without a topic anchor, Claude has no signal for what to emphasise or skip during ingest. Be specific — "AI safety research with a focus on mechanistic interpretability" is useful; "tech stuff" is not.

If you'd rather edit `CLAUDE.md` by hand, open it, find the `<!-- REPLACE THIS LINE -->` block in the Overview section, and replace it with one paragraph describing your knowledge base. Then run `/wiki-init` just for the directory verification.

---

## 4. The four operations at a glance

| Operation | Slash command | Non-interactive fallback | When |
|---|---|---|---|
| Ingest | `/wiki-ingest` | `claude -p "<body of wiki-ingest.md>"` | Every time you drop a source in `raw/` |
| Query | `/wiki-query <question>` | `claude -p "/wiki-query Your question here"` | When you have a question the wiki might answer |
| Lint | `/wiki-lint` | `claude -p "<body of wiki-lint.md>"` | Weekly, or after a batch of ingests |
| Compile | `/wiki-compile` | `claude -p "<body of wiki-compile.md>"` | When the index feels stale or you've manually moved files |

All four read `CLAUDE.md` first and follow its rules. The slash commands are shortcuts under `.claude/commands/`.

---

## 5. Walkthrough — ingest a source, step by step

This is the operation you'll run most often. Three examples: an article, a paper (PDF), a transcript.

### 5.1 Ingest an article

1. **Find a source worth keeping.** A blog post, a Twitter/X thread, a newsletter — anything substantive you want to remember and connect to other things.
2. **Save it as markdown** in `raw/articles/`. Use Obsidian's Web Clipper extension (recommended) or just copy-paste the text into a new note:
   ```
   raw/articles/karpathy-llm-knowledge-bases.md
   ```
   Put the URL at the top (`Source: <url>`) so Claude can cite it.
3. **Run `/wiki-ingest`** in an interactive Claude Code session.
4. **Wait.** Claude reads the source fully, then produces:
   - One `wiki/sources/{slug}.md` summary (200–500 words for articles)
   - N concept pages / stubs under `wiki/concepts/`
   - M entity pages / stubs under `wiki/entities/`
   - Updated `wiki/index.md`
   - Appended entry to `wiki/log.md`
5. **Verify in Obsidian:**
   - Every `[[wikilink]]` in the new summary is clickable (not red).
   - Graph view shows the new source connected to its concepts and entities.
   - Properties pane shows typed fields on every new page.

### 5.2 Ingest a paper (PDF)

1. **Drop the PDF in `raw/papers/`**. You can rename the file if you want; the raw folder doesn't need kebab-case (wiki files do).
2. **Run `/wiki-ingest`**.
3. If the paper is **> ~50 pages** (books, theses, long reports), Claude will **stop and propose a chapter-split plan** before writing anything. Approve or amend the plan, then tell Claude to proceed.
4. Claude uses the **paper template** (`templates/paper-summary.md`) because the source is in `raw/papers/`. The summary includes:
   - Bibliographic frontmatter: `authors`, `venue`, `doi`, `arxiv`, `page_count`
   - Inline page citations on quotes and specific claims: `(p. 7)`, `(pp. 11–13)`
   - Math in MathJax, not code spans: `$d_{\text{model}} = 512$`, block equations on their own lines
   - "Figures / equations of note" section with figures **described in prose** (not extracted as images, unless you explicitly ask)
5. **Verify** as above, plus spot-check one or two page citations against the PDF.

### 5.3 Ingest a transcript

1. **Drop the transcript markdown in `raw/transcripts/`**. YouTube transcripts, podcast transcripts, meeting transcripts all work.
2. **Run `/wiki-ingest`**.
3. Claude uses the generic **source-summary template** (not paper) because transcripts don't have bibliographic structure.
4. **Caveat:** transcripts are dense with filler. The summary should extract the argument and key claims, not the conversational texture. If Claude's summary reads like "the speaker said X, then said Y, then said Z" instead of "the argument is X because Y, exemplified by Z," tell it to resynthesize.

### 5.4 Ingest multiple sources at once

```bash
claude -p "/wiki-ingest"   # processes every unprocessed raw/ file
```

Or, interactively, just tell Claude: *"Ingest everything new in `raw/`."*

Two caveats:

- **Batch ingests share context.** Claude reads all the sources first, which is good for cross-linking but can exhaust context on long papers. If you're ingesting 5+ papers, do them one at a time.
- **Order matters for cross-references.** Ingest older papers before newer ones if the newer ones cite them — concepts get stubbed on first mention, then promoted on second mention; order affects which paper gets credit for the full-page promotion.

---

## 6. Walkthrough — ask a question, step by step

This is the operation that makes the wiki compound.

### 6.1 Format the question

Ask something the wiki **could plausibly answer** from its current sources. Bad examples for a small vault:

- *"What's the best <any topic>?"* — subjective, rarely answerable from sources alone.
- *"Why is the sky blue?"* — if you haven't ingested a source on atmospheric optics, no answer possible.

Good shapes:

- *"What did paper A change relative to paper B?"* — cross-source synthesis.
- *"How does <thing described in one source> actually work?"* — single-source retrieval.
- *"What's the <named concept> the wiki has on it?"* — concept-page retrieval with citations.

### 6.2 Run the query

```
/wiki-query What's the central claim of the source I ingested yesterday?
```

Or non-interactive:

```bash
claude -p "/wiki-query What's the central claim of the source I ingested yesterday?"
```

### 6.3 What Claude does

1. Reads `wiki/index.md` first.
2. Identifies candidate pages from the index.
3. Reads only those pages.
4. **If coverage is insufficient, Claude tells you which raw sources to add — it does not invent facts.** This is non-negotiable.
5. Synthesizes an answer with `[[wikilink]]` citations to every non-obvious claim.
6. Files the answer to `wiki/outputs/{question-slug}.md` using the output template.
7. Updates `wiki/index.md` and appends to `wiki/log.md`.

### 6.4 Review the output

Open `wiki/outputs/{slug}.md` in Obsidian. The output should have:

- A **short answer** (2–4 sentences).
- A **full answer** with structured sections and inline citations.
- A **"What I would add"** section flagging sources the wiki is missing.

If any claim looks invented or any citation looks fake, tell Claude to fix it. **Always spot-check citations against the source summaries.**

### 6.5 Decide: keep as output, or promote to synthesis

- **Keep as output:** one-off answer. Lives in `wiki/outputs/`. Default.
- **Promote to synthesis:** the answer is a durable cross-cutting analysis that you want to treat as first-class wiki content. Move to `wiki/syntheses/{slug}.md`, update `type: synthesis` in frontmatter. Only do this for answers that other queries will cite later.

Per `CLAUDE.md`, syntheses are **explicit-request only** — Claude won't auto-create them.

---

## 7. Walkthrough — run lint, step by step

### 7.1 When to run

- After a batch of ingests (e.g. once per week of normal usage).
- Before a graduation re-evaluation (see §15).
- When you notice something looks off (red links, duplicate pages).

### 7.2 Run it

```
/wiki-lint
```

### 7.3 What it produces

A timestamped report at `wiki/outputs/lint-report-YYYY-MM-DD.md` with sections:

- **Auto-fixed** — things Claude fixed without asking (frontmatter drift, broken links patched with stubs, `source_count` recount, kebab-case renames).
- **Needs my attention** — promotion candidates, contradictions, stale content, orphans, rule-calibration proposals.
- **Suggested next sources** — what would plug current gaps.
- **Suggested next questions** — questions the wiki can answer now vs ones it can't.

### 7.4 Act on the report

Walk the "Needs my attention" list top to bottom. For each item:

- **Promotion candidate:** if you agree, tell Claude to promote it. *"Promote `scaled-dot-product-attention` to a full page."*
- **Contradiction:** resolve it yourself (your call, per `CLAUDE.md`), or ingest a newer source that settles it.
- **Orphan:** either link it from somewhere, or mark `status: deprecated`.
- **Rule calibration:** edit `CLAUDE.md` to tighten the rule.

### 7.5 Commit

After acting on the report, commit. Keep the lint report itself in the repo — future lints will cross-reference it.

---

## 8. Walkthrough — compile (rebuild index)

Rarely needed; the ingest / query / lint operations already regenerate the index. Run `/wiki-compile` when you've **manually edited files** (renamed, moved, deleted, or added by hand) and want Claude to resynchronize the index without changing page content.

```
/wiki-compile
```

Output: `wiki/index.md` is regenerated from the filesystem; `wiki/log.md` gets one `compile` entry; no page bodies are touched.

---

## 9. Workflow rhythm — a realistic weekly cadence

| Frequency | Activity |
|---|---|
| As sources arrive | Drop in `raw/`; run `/wiki-ingest` |
| 2–3× / week | Run a `/wiki-query` on something you've been wondering about |
| Weekly | Run `/wiki-lint`; act on the report |
| Occasionally | Manually promote a stub you've noticed getting cited a lot |
| Monthly | Re-read the "Suggested next sources" from recent lint reports; curate |
| Quarterly or at milestones | Re-evaluate graduation triggers (`docs/graduation-YYYY-MM-DD.md`) |

Three interactions per week is enough for the wiki to grow steadily. More is fine; less and it stagnates.

---

## 10. File tree — what goes where, and who owns it

```
z-wiki/
├── .claude/                  ← Claude Code config (slash commands + vendored skills)
│   ├── commands/             ← /wiki-init, /wiki-ingest, /wiki-query, /wiki-lint, /wiki-compile
│   └── skills/               ← Vendored kepano/obsidian-skills (5 skills, auto-discovered)
├── .obsidian/                ← Obsidian config (partially gitignored)
├── CLAUDE.md                 ← The spec. Auto-loaded by Claude at session start.
├── README.md                 ← 30-second overview + quickstart
├── raw/                      ← YOU own this. Immutable once files land.
│   ├── articles/
│   ├── papers/               ← PDFs + .md extractions; paper-summary template triggered here
│   ├── transcripts/
│   └── assets/               ← Images from clipped articles (Obsidian default)
├── wiki/                     ← CLAUDE owns this entirely. You read; Claude writes.
│   ├── index.md              ← Master catalog, regenerated on every op
│   ├── log.md                ← Append-only changelog
│   ├── sources/              ← One summary per raw source
│   ├── concepts/             ← One page per concept (stubs + full pages)
│   ├── entities/             ← People, orgs, tools, libraries, projects
│   ├── syntheses/            ← Crystallized cross-cutting analyses (explicit-request only)
│   ├── outputs/              ← Filed query answers + lint reports
│   ├── views/                ← Ornamental Obsidian Bases (.base files)
│   ├── canvases/             ← Ornamental Obsidian Canvases (.canvas files)
│   └── attachments/images/   ← Claude-generated charts/diagrams
├── templates/                ← The rules Claude follows when creating pages
│   ├── source-summary.md
│   ├── paper-summary.md
│   ├── concept.md
│   ├── entity.md
│   ├── synthesis.md
│   ├── output.md
│   └── stub.md
├── docs/                     ← Meta documentation (this guide, plan, graduation reports)
│   ├── GUIDE.md              ← You're reading it
│   ├── obsidian-skills-provenance.md
│   └── graduation-*.md
├── .gitignore
└── .gitattributes
```

**Ownership rule to memorize:** you never hand-edit `wiki/`; Claude never touches `raw/`. If you catch yourself editing a wiki page, either (a) revert and tell Claude to make the change, or (b) promote the edit into a CLAUDE.md rule change so future Claude sessions apply it consistently.

---

## 11. Conventions that matter (cheatsheet)

### Filenames

- `wiki/` files: **lowercase kebab-case ASCII**, no spaces, no underscores. Globally unique across the whole `wiki/` tree.
- `raw/` files: can be anything. Claude derives a kebab-case slug for the wiki summary.
- Source summaries: `{author-lastname}-{year}-{short-title}.md` (e.g. `vaswani-2017-attention-is-all-you-need.md`) when authors/year are known.

### Links

- `[[shortest-path]]` — Obsidian resolves by filename
- `[[slug|display text]]` — custom display
- `[[slug#Heading]]` — link to a heading
- `[[slug#^block-id]]` — link to a block (define the block by appending `^block-id` to a paragraph)

### Frontmatter (every wiki page)

```yaml
---
title: "Page Title"
type: source | concept | entity | synthesis | output | stub
status: draft | review | final
date_created: YYYY-MM-DD
date_modified: YYYY-MM-DD
summary: "One to two sentences."
tags:
  - domain-tag
---
```

Per-type additions: see `CLAUDE.md` → Frontmatter schema.

### Callouts

```markdown
> [!warning] Contradiction
> Source A claims X (p. 7); source B claims ¬X (p. 12).

> [!note]
> Non-obvious mechanism worth flagging.
```

Obsidian renders as colored callouts. GitHub renders as blockquotes — degrades gracefully.

### Math (MathJax)

Inline: `$d_{\text{model}} = 512$` renders as $d_{\text{model}} = 512$

Block (on its own lines, with blank lines above and below):

```markdown

$$\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right) V$$

```

**Never wrap math in backticks** — those render as monospace code, not typeset math.

### Tags

Inline: `#tag` or `#nested/tag`
In frontmatter:
```yaml
tags:
  - project
  - active
```

### Stubs vs full pages

- **Stub:** `type: stub`, `source_count: 1`, frontmatter + one-sentence definition + link back to its source. Created on-ingest for any referenced concept.
- **Full page:** `type: concept | entity | synthesis`, written when `source_count ≥ 2` or when inbound references justify it (the lint report flags candidates).

---

## 12. Troubleshooting

### "Obsidian shows red wikilinks"

Links that don't resolve to any file. Run `/wiki-lint` — the auto-fix step creates stubs for broken links.

### "Math shows as `$...$` literal text, not typeset equations"

Settings → Editor → LaTeX / MathJax is probably off. Turn it on. If it's already on, check that the math isn't wrapped in backticks (common mistake): `` `$E = mc^2$` `` renders as code, not math. Remove the backticks.

### "A `.base` file shows a YAML error"

Open `.claude/skills/obsidian-bases/SKILL.md` → Troubleshooting. Common causes:
- A formula like `if(done, "Yes", "No")` wrapped in double quotes instead of single quotes.
- A property referenced as `formula.total` without defining `total` in the `formulas:` section.
- A `:` in an unquoted string, e.g. `displayName: Status: Active`.

### "A `.canvas` file won't open"

Claude-generated canvases should be valid JSON with unique node IDs. If yours fails, open `.claude/skills/json-canvas/SKILL.md` → Validation Checklist. Most common: duplicate IDs or an edge pointing at a non-existent node.

### "Claude created 15 stubs from one article — that's too many"

Tighten the rule: in `CLAUDE.md` → Quality bar, add *"Only link concepts that are substantively discussed in the source, not ones casually mentioned in passing."* Tell Claude to re-run the ingest.

### "Claude is rewriting pages instead of appending"

The single most common failure mode. `CLAUDE.md` already says *"append, don't rewrite from scratch,"* but Claude sometimes forgets on large ingests. Fix:
1. Spot-check with `git diff` after each ingest.
2. If a rewrite happened, `git checkout wiki/concepts/page-name.md` to restore.
3. Tell Claude explicitly: *"Update in place by appending; do not rewrite prose that hasn't changed."*

### "Hit Claude usage limits partway through a batch ingest"

Smaller batches. Process 3–5 sources at a time. If it's a pattern, consider Claude Max plans.

### "I accidentally edited a wiki page by hand"

Two options:
- `git diff wiki/path/to/page.md` — see what you changed; decide to keep or revert.
- If keeping: tell Claude what you edited and why, so future ingests respect it.
- If reverting: `git checkout wiki/path/to/page.md`.

### "I hit the fact-forcing gate during commits / edits"

The repo has hooks that require justification for destructive and edit operations. Present facts briefly (call sites, no-existing-equivalent check, data-file description if any, user instruction quoted) and retry. The gate is a safety feature, not a bug.

### "Obsidian's graph view is overwhelming at N pages"

Obsidian → Graph settings (right panel icon in graph view) → tune filters (hide stubs, filter by tag, hide specific folders). Or bump the plan's graduation trigger for splitting the index by type.

---

## 13. Extending the system

### Add a new source type

Say you start recording voice memos and want `raw/voice-memos/`.

1. `mkdir raw/voice-memos`; add a `.gitkeep`.
2. Optionally write `templates/voice-memo-summary.md` if the shape differs meaningfully from `source-summary.md` (speaker, duration, location, etc.).
3. In `CLAUDE.md` → Layers section, add the new subfolder.
4. In `CLAUDE.md` → INGEST step 2b, add the template-selection rule if you made a new template.
5. Commit.

### Add a new slash command

1. Create `.claude/commands/<name>.md` with frontmatter. Minimal:
   ```markdown
   ---
   description: <one clause, shown in the / autocomplete picker>
   allowed-tools: Read, Write, Bash, Glob, Grep
   ---

   # <Name>

   Read `CLAUDE.md`. <Explain the operation.>
   ```

   Richer frontmatter for better auto-discovery and UX:
   ```markdown
   ---
   description: <one clause>
   argument-hint: "<arg-or-[optional]>"           # shown while typing the command
   when_to_use: <trigger phrases the model uses for auto-invocation>
   allowed-tools: Read, Write, Bash, Glob, Grep
   model: haiku | sonnet | opus                   # optional: pin a model for this command
   effort: low | medium | high | max              # optional: pin effort level
   context: fork                                  # optional: run in isolated subagent context
   agent: general-purpose                         # used with context: fork
   ---
   ```
   Full field list: 14 fields total — see the official Claude Code slash-commands docs. The five used by this template (`description`, `argument-hint`, `when_to_use`, `allowed-tools`, plus the model has auto-discovery via `description`) are enough for almost any operation.

2. Restart Claude Code to pick up the new command (or run `/reload-plugins`).

### Update a template

Edit `templates/<name>.md`. Future Claude sessions will use the new shape. **Past pages don't auto-update** — if the change matters, run `/wiki-lint` and ask Claude to bring old pages into compliance, or just let them drift until they're touched again.

### Update `CLAUDE.md`

Be surgical. Every line in `CLAUDE.md` is loaded into every Claude session — bloat costs tokens. When in doubt, add a rule under existing sections (File conventions, Quality bar) rather than creating new sections.

### Write a synthesis (crystallize an output)

Two paths:

- **Explicit ask:** tell Claude *"Write a synthesis on X, drawing from [[y]] and [[z]]."*
- **Output promotion:** find a `wiki/outputs/*.md` file you keep citing. Tell Claude *"Promote `output-slug` to a synthesis."* It moves the file to `wiki/syntheses/`, updates `type`, and re-rewrites with the synthesis template.

Syntheses are **first-class** — once created, they should be cited from concept pages' Related sections and from other syntheses.

---

## 14. Advanced — Bases, Canvas, CLI, Defuddle

### Obsidian Bases (dynamic views)

Create `.base` files under `wiki/views/`. Example: `wiki/views/sources-by-year.base` already exists and renders all sources grouped by publication year.

Write new ones by copying the existing file, editing filters/formulas/views, and opening in Obsidian. Syntax: `.claude/skills/obsidian-bases/SKILL.md`. Validate via `/wiki-lint` — it now checks `.base` YAML.

**Rule:** Bases are ornamental. Never use a `.base` file as primary navigation. The load-bearing index is always `wiki/index.md`.

### Obsidian Canvas (visual workspaces)

Create `.canvas` files under `wiki/canvases/` for mind-maps, architecture diagrams, or dependency graphs that prose can't capture. Spec: `.claude/skills/json-canvas/SKILL.md`.

**Rule:** Canvases are ornamental. Anything expressed in a canvas must also exist in plain markdown elsewhere in `wiki/`. The canvas is a viewing lens, not a source of truth.

### Obsidian CLI

Install: see https://help.obsidian.md/cli. Then Claude can drive Obsidian from the shell — reading notes, running searches, setting properties, reloading plugins:

```bash
obsidian search query="transformer"
obsidian property:set name="status" value="review" file="transformer"
obsidian backlinks file="transformer"
```

Skill: `.claude/skills/obsidian-cli/SKILL.md`.

### Defuddle (clean web extraction)

Install: `npm install -g defuddle`. Then when Claude needs to fetch a standard web page for a source, it'll prefer `defuddle parse <url> --md` over `WebFetch` — strips navigation, ads, and boilerplate. Cheaper and cleaner.

Skill: `.claude/skills/defuddle/SKILL.md`.

### Multi-machine via git

```bash
# On machine A:
git remote add origin <url>
git push -u origin main

# On machine B:
git clone <url> z-wiki
cd z-wiki
# open as Obsidian vault; start Claude Code; you're ready
```

Obsidian settings live in `.obsidian/` (partially committed), so the second machine inherits your link format, attachment folder, and excluded files. Plugins are gitignored by default — install them on each machine manually, or commit `.obsidian/plugins/` explicitly if you want them synced.

---

## 15. When v1 isn't enough — graduation discipline

The architecture as shipped is optimised for the **low-hundreds-of-pages regime**. Past that, specific scaling mechanisms become necessary — hybrid search (BM25 + vector), hierarchical indexes, automation, confidence scoring, two-model validation. None of it is pre-built here, because adding complexity before it's needed is the failure mode.

**Rule: do not unlock v2 features on intuition.** When you think "this is getting slow" or "I wish it knew X about Y," ask whether a specific threshold has fired, not whether it feels nice to have. Most "v2 urges" are v1 hygiene in disguise (promote a stub, add a source, calibrate a rule).

Suggested triggers to watch (copy these into your own `docs/graduation-<date>.md` and evaluate them periodically):

| Unlock | Trigger |
|---|---|
| Hybrid search (BM25 + vector) | Sources > 50 OR `grep wiki/` > 2s |
| Hierarchical index (per-section `_index.md` load-bearing) | `wiki/index.md` > 500 lines OR > 10k tokens |
| Cron / scheduled automation | Manual `/wiki-ingest` ≥5×/week for ≥2 weeks |
| Confidence scoring / supersession | ≥5 pages with open contradictions >2 weeks |
| Two-model validation | Any confirmed hallucinated fact or citation |
| Knowledge-graph layer (typed edges) | ≥3 queries/week needing graph traversal |

Write a new `docs/graduation-<YYYY-MM-DD>.md` whenever any trigger looks close or fires. Record actual metrics, evaluate every trigger, make one explicit decision. That habit is what keeps the system from bloating before it needs to.

---

## 16. Slash commands — quick reference

**Core lifecycle** (the four canonical operations):

| Command | What it does | Common invocation |
|---|---|---|
| `/wiki-ingest [path]` | Process new files in `raw/` into the wiki | After dropping sources, or automatically after `/wiki-add` |
| `/wiki-query <question>` | Answer a question using only the compiled wiki | When you have a question |
| `/wiki-lint` | Audit the wiki; auto-fix what's fixable, report the rest | Weekly |
| `/wiki-compile` | Regenerate `wiki/index.md` from the filesystem | After manual file moves/renames |

**Helpers** (quality-of-life commands; not part of the knowledge lifecycle):

| Command | What it does | Common invocation |
|---|---|---|
| `/wiki-init` | First-run: topic-setup wizard + directory scaffold. Re-runs: directory/template verification only. | Once at setup; re-run any time the structure looks off |
| `/wiki-add <url-or-path>` | Fetch a URL (or copy a file) into the right `raw/` subfolder; offer to ingest | When adding a source end-to-end |
| `/wiki-status` | Read-only: print vault counts, stubs near promotion, recent activity | Any time you want a quick sanity check |
| `/wiki-new-template <name>` | Scaffold a new template; optionally wire it into `CLAUDE.md → INGEST` | When adding a new kind of source material |

All eight read `CLAUDE.md` first. The core four write to `wiki/log.md`. `/wiki-status` writes nothing. `/wiki-init`, `/wiki-add`, and `/wiki-new-template` may edit `CLAUDE.md` and `raw/` — the only commands allowed to.

---

## 17. One-line mental model

> **You curate sources. Claude writes the wiki. Git remembers everything. Obsidian shows the whole thing. The filing loop makes it compound.**

That's the system. The rest is detail.
