---
name: defuddle
description: Extract clean markdown content from web pages using Defuddle CLI, removing clutter and navigation to save tokens. Use instead of WebFetch when the user provides a URL to read or analyze, for online documentation, articles, blog posts, or any standard web page. Do NOT use for URLs ending in .md — those are already markdown, use WebFetch directly.
---

# Defuddle

Use Defuddle CLI to extract clean readable content from web pages. Prefer over WebFetch for standard web pages — it removes navigation, ads, and clutter, reducing token usage.

If not installed: `npm install -g defuddle`

## Usage

Always use `--md` for markdown output:

```bash
defuddle parse <url> --md
```

Save to file:

```bash
defuddle parse <url> --md -o content.md
```

Extract specific metadata:

```bash
defuddle parse <url> -p title
defuddle parse <url> -p description
defuddle parse <url> -p domain
```

## Output formats

| Flag | Format |
|------|--------|
| `--md` | Markdown (default choice) |
| `--json` | JSON with both HTML and markdown |
| (none) | HTML |
| `-p <name>` | Specific metadata property |

## Handling large pages (>5MB)

Defuddle's URL fetcher has a hard 5MB cap (not configurable). When you
hit `Error: Page too large (NMB, max 5MB)`, bypass the fetcher by
downloading the HTML yourself and passing the local file:

```bash
curl -L --compressed -o /tmp/page.html "<url>"
defuddle parse /tmp/page.html --md -o /tmp/page.md
```

`defuddle` only size-checks on fetch, not on local-file parse, so this
sidesteps the limit entirely.

## Post-processing: strip inline data URIs

Many large pages (research blog posts, technical articles) embed figures
as base64 data URIs inline in `<img>` tags. Defuddle preserves them
verbatim, which can balloon a 200 KB article into 7+ MB of markdown
(mostly useless base64). Always strip them:

```bash
sed -E 's|!\[([^]]*)\]\(data:[^)]+\)|![\1](<inline-image-stripped>)|g' \
    raw.md > clean.md
```

Real page images use `<img src="https://...">` URLs, not data URIs — so
this strip only targets the noise. Apply unconditionally when the raw
output is larger than the prose warrants (rule of thumb: >500 KB for an
article).

## Full pipeline for a URL

```bash
# 1. Try the simple path first
defuddle parse "<url>" --md -o raw.md \
  || (curl -L --compressed -o page.html "<url>" && \
      defuddle parse page.html --md -o raw.md)

# 2. Always strip inline data URIs
sed -E 's|!\[([^]]*)\]\(data:[^)]+\)|![\1](<inline-image-stripped>)|g' \
    raw.md > clean.md
```
