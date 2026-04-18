---
description: Answer a question using only the compiled wiki; file the full answer and print a polished summary in the terminal.
argument-hint: "<question>"
when_to_use: Use when the user asks a question the wiki could plausibly answer from its compiled sources. Reads wiki/index.md first, shortlists candidate pages, answers with wikilink citations, files the full answer under wiki/outputs/, then prints a scannable summary to the terminal. Never invents facts — if coverage is insufficient, says so and lists missing sources. Also triggered by phrases like "query the wiki", "what does the wiki say about", "ask the vault".
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Wiki Query

Read `CLAUDE.md` for conventions. Follow the QUERY operation exactly as specified there.

## The question
$ARGUMENTS

## Non-negotiable rules

- Start by reading `wiki/index.md`. Then read only the pages the index points you to.
- Cite every non-obvious claim with a `[[wikilink]]` to a source summary or concept page.
- If the wiki cannot answer the question, say so and list the raw sources that would need to be added. Do not invent facts, do not use external web knowledge.
- Save the full answer to `wiki/outputs/{question-slug}.md` using `templates/output.md`.
- Update `wiki/index.md` and append to `wiki/log.md`.
- **After filing, print a polished summary to the terminal.** The file has the depth; the terminal output is the scannable signal the user reads immediately without opening anything.

## Terminal output format

Print this block AFTER the file is saved. Use markdown — Claude Code renders it as styled text. Do NOT print the full prose inline; the whole point of filing is that the full answer is one file-open away.

Exact shape:

```markdown
---

### 🔍 `<the original question>`

**Short answer**
<2–4 sentences. Matches or summarises the short-answer section of the filed output. Plain prose — no bullets, no headers, no code blocks.>

**Sources cited** (<N>)
- `[[wikilink-1]]` — one-line purpose of this citation
- `[[wikilink-2]]` — one-line purpose
- ... (typically 3–10)

**Gaps** (<N>)
- What's missing to strengthen this answer — one line each
- (Omit the whole "Gaps" section if the filed output has no "What I would add" items)

**Filed**
📄 `wiki/outputs/<slug>.md`

---
```

Length target: ≤ 25 lines of terminal output. If the answer needs more depth, that depth goes in the filed output, not in the terminal print.

## Failure mode

If the wiki can't answer the question (zero relevant sources indexed), don't file anything. Instead print:

```markdown
---

### 🔍 `<the original question>`

**No coverage.** The wiki has no source that speaks to this. To answer it, you would need to ingest one of:

- <concrete suggestion for a source type / URL / paper>
- <second suggestion>

Run `/wiki-add <url-or-path>` to add a source, or drop one into `raw/` manually and run `/wiki-ingest`.

---
```

The "No coverage" response is the only case where the command writes nothing to disk (no output file, no index update, no log entry).

## Reporting

The terminal block above IS the report. No separate structured summary needed.
