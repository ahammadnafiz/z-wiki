---
description: Add a new raw source from a URL or file path, then optionally ingest.
argument-hint: "<url-or-path>"
when_to_use: Use when the user wants to add a new source to the wiki — a URL to an article, a path to a PDF or markdown file on disk. One-shot replacement for the "save file to raw/ manually, then /wiki-ingest" dance. Triggered by phrases like "add this source", "add this url", "add this paper", "grab this article".
allowed-tools: Read, Write, Edit, Bash, WebFetch, Glob, Grep
---

# Wiki Add

Add a new source to `raw/` and (optionally) ingest it. Arg (`$ARGUMENTS`): a URL or a local file path.

## Dispatch

### If `$ARGUMENTS` starts with `http://` or `https://`

1. **Fetch the content.**
   - **Prefer `defuddle`** (installed via `npm install -g defuddle`) for article-style URLs: blog posts, newsletters, X/Twitter long-forms, news sites, Reddit. It strips navigation and boilerplate — cheaper and cleaner than WebFetch. Skill reference: `.claude/skills/defuddle/SKILL.md`.
   - **Use `WebFetch` directly** for: arXiv HTML (`arxiv.org/abs/` and `arxiv.org/html/`), GitHub pages (`github.com/.../blob/.../README.md`), raw `.md` URLs, anything already structured.
   - If the URL returns an error or empty content, stop and report — do not write an empty file.

2. **Derive a slug.**
   - Use the page `<title>` (or `<h1>`) as the basis; kebab-case, ASCII, no spaces/underscores/uppercase.
   - Append `-{year}` if the source has a clear publication year and the slug would otherwise be ambiguous.
   - Confirm the slug with the user if it came out weird (long, ambiguous, collides with existing).
   - Never overwrite an existing file. If `raw/articles/{slug}.md` already exists, propose a different slug or stop.

3. **Write to `raw/articles/{slug}.md`.** Prepend a frontmatter-like header Claude can cite later:
   ```markdown
   ---
   Source: <original-url>
   Fetched: YYYY-MM-DD
   ---

   <extracted markdown body>
   ```

### If `$ARGUMENTS` is a local file path

1. **Dispatch by extension:**
   - `.pdf` → `raw/papers/{slug}.pdf`. Use the filename (minus extension) as the slug, kebab-cased.
   - `.md` or `.txt` → ask the user: *"Is this an article, a paper extraction, or a transcript?"* Copy to the corresponding `raw/{articles,papers,transcripts}/{slug}.md`. Default to `raw/articles/` if the user says "article" or doesn't care.
   - Any other extension → refuse with a clear message listing supported types (`.pdf`, `.md`, `.txt`).

2. **Never overwrite.** If the target file already exists, propose a different slug or stop.

### Refusal rules

- Do not fetch URLs resolving to `localhost`, `127.0.0.1`, `0.0.0.0`, or private IP ranges (`10.*`, `172.16–31.*`, `192.168.*`). Report the refusal.
- Do not write empty or obviously-stub content. If the fetch returned <200 chars of body text, stop and tell the user.
- Do not create files outside `raw/articles/`, `raw/papers/`, or `raw/transcripts/`.

## After placing the file

1. Report the path of the new file.
2. Ask the user: *"Ingest now? (y/n)"*
   - **Yes** → invoke `/wiki-ingest <new-file-path>`. Follow the INGEST operation in `CLAUDE.md` for just that one file.
   - **No** → stop. The user can run `/wiki-ingest` later whenever they want.

## Reporting

- Source path written
- Slug used
- Size of fetched/copied content
- Whether ingestion was triggered
