---
name: citation-forensics
description: "Verify every citation in a paper is real, correctly attributed, and used in a context the cited work actually supports — catching hallucinated references, wrong years/venues/authors, and wrong-context citations. A hot zone for machine-generated papers. Works at L0 (PDF-only). Span-anchored to the evidence ledger; fresh cross-model thread per entry. Triggers: \"citation forensics\", \"check the references\", \"hallucinated citations\", \"引用核对\"."
argument-hint: [paper-dir | claims.json]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, mcp__codex__codex, mcp__mcp-dblp__search, mcp__mcp-dblp__fuzzy_title_search
---

# Citation Forensics — are the references real and honestly used?

> Adapted from ARIS `citation-audit`. Autoresearch pipelines fabricate plausible-
> looking references and cite real papers for claims they do not make. Three
> layers: existence → metadata → context.

Audit citations for: **$ARGUMENTS** (uses `citation`-type claims in `claims.json`).

## Step 1 — Pull (cite-key, context) pairs from the ledger

Every `type: "citation"` claim already carries `refs` (the cite keys) and the
surrounding sentence as `text_span`. Group by cite key; each key inherits all its
citing-sentence spans. Also read the `.bib` for the claimed metadata.

## Step 2 — Layer 1+2: existence & metadata (deterministic-ish)

For each cited key, verify against canonical sources (don't trust the `.bib`):

```
mcp__mcp-dblp__search / fuzzy_title_search   # venue, authors, year
WebSearch / WebFetch                          # arXiv id / DOI resolves to THIS paper
```

- **HP-CITE-HALLUC** (critical) — no paper exists at the claimed id/venue, or
  authors/title are fabricated.
- metadata wrong (major) — real paper, wrong year/venue/authors/version.
- A typo'd-but-resolvable id is `FIX`, not fabrication (lower severity).

## Step 3 — Layer 3: context (cross-model, fresh thread per entry)

Existence is mechanical; *context* needs judgment. For each cited key with citing
spans, a fresh `mcp__codex__codex` (gpt-5.5 xhigh, read-only) is asked:

```
Here is a citation key, the canonical paper it refers to, and the sentence(s) in
which the manuscript cites it. Does the cited paper actually support the claim each
sentence uses it for?

Cited paper: <title / abstract / canonical metadata>
Citing spans (verbatim, with claim_id):
  - [C0xx] "<sentence>"

Output per span a finding (schemas/finding.schema.json) ONLY if there is a real
mismatch:
  pattern_id: HP-CITE-CONTEXT, severity: major,
  evidence:[{claim_id, span, location}],
  description: what the cited paper actually establishes vs how it is used,
  false_positive_risk: (high if "see also / contrast" framing is plausible),
  recommended_reviewer_action.
Never fabricate the cited paper's content; if unsure, say so and set verdict_local
needs_external_check.
```

Fresh thread per entry (REVIEWER_BIAS_GUARD). Never `codex-reply` across entries.

## Step 4 — Validate + emit

Keep only findings whose `claim_id` + verbatim `span` exist in the ledger. Write
`citation-forensics.findings.json`. Save traces. No verdict here.

## Key rules

- **Don't trust the bib** — verify against DBLP / arXiv / publisher.
- **Wrong-context needs the cited paper's actual content**, not a guess; uncertain →
  `needs_external_check`.
- **Uncited bib entries** are detect-only and not flagged unless explicitly requested.
- **Detect-only**; never rewrite the `.bib` or `.tex`.
