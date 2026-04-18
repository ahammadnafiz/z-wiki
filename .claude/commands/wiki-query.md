---
description: Answer a question using only the compiled wiki.
argument-hint: "<question>"
when_to_use: Use when the user asks a question the wiki could plausibly answer from its compiled sources. Reads wiki/index.md first, shortlists candidate pages, answers with wikilink citations, and files the answer under wiki/outputs/. Never invents facts — if coverage is insufficient, says so and lists missing sources. Also triggered by phrases like "query the wiki", "what does the wiki say about", "ask the vault".
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Wiki Query

Read `CLAUDE.md` for conventions. Follow the QUERY operation exactly as specified there.

## The question
$ARGUMENTS

## Non-negotiable rules
- Start by reading `wiki/index.md`. Then read only the pages the index points you to.
- Cite every non-obvious claim with a `[[wikilink]]` to a source summary or concept page.
- If the wiki cannot answer the question, say so and list the raw sources I would need to add. Do not invent facts, do not use external web knowledge.
- Save the answer to `wiki/outputs/{question-slug}.md` using `templates/output.md`.
- Update `wiki/index.md` and append to `wiki/log.md`.

## Reporting
- Slug of the output file
- Pages cited
- Gaps flagged (if any)
