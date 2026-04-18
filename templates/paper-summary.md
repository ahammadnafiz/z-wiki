---
title: "{{title}}"
type: source
status: draft
date_created: {{TODAY}}
date_modified: {{TODAY}}
summary: "Two-sentence synthesis of the paper's core contribution and relevance."
tags:
  - raw-source
  - paper
source_url: "{{url_or_doi_or_arxiv}}"
source_path: "raw/papers/{{filename}}"
authors:
  - "{{author-1}}"
  - "{{author-2}}"
published: "{{year}}"
venue: "{{journal_or_conference_or_unknown}}"
doi: "{{doi_or_empty}}"
arxiv: "{{arxiv_id_or_empty}}"
source_type: paper
page_count: {{int}}
---

# {{title}}

**Source:** [[{{raw_filename_without_ext}}]] · {{source_url}}
**Authors:** {{author list}}
**Published:** {{year}} · {{venue}}

## Thesis
One paragraph. What does the paper claim and why does it matter?

## Contribution
What's new here? Distinguish from prior work cited by the authors.

## Method
High-level description of how the claim is tested or built. One paragraph.

## Key results
- Result 1 (p. 7).
- Result 2 (pp. 11–13).

## Key concepts
- **[[concept-1]]** — one-line takeaway (p. N).
- **[[concept-2]]** — one-line takeaway (pp. N–M).

## Entities
- [[entity-1]]
- [[entity-2]]

## Notable quotes
> "..." — (p. 7)
> "..." — (p. 12)

## Figures / equations of note
- Fig. 3 (p. 9): what it shows, one sentence, in prose.
- Eq. 2 (p. 11): $y = f(x)$ — plain-language meaning. For display/block equations use `$$...$$` on their own lines.

## Connections
- Extends: [[related-paper]] on ...
- Contradicts: [[other-paper]] on ... (⚠️ flag on that page)

## Limitations / open questions
- ...

## My notes
_(Optional.)_
