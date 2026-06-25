# Positioning — where Anti-Autoresearch sits, and the gap it fills

## The shift that matters

As LLM-driven paper *and* review generation became routine in 2025–2026, venues
moved from "is AI allowed?" to disclosure policies, AI-assisted-review audits, and
desk-rejections for undisclosed generation. But the question a program committee
actually needs answered is **not** stylometric. A human can write a dishonest
paper; an LLM can write an honest one. The load-bearing question is:

> **Is the paper internally consistent and supported by its own evidence?**

That is a *substantive integrity* question, and it is precisely where
machine-generated research fails — pipelines optimize a narrative and hallucinate
*local* coherence.

## The three existing clusters

**A — AI-text detectors.** Pangram, GPTZero, DetectGPT / Fast-DetectGPT,
Binoculars, and the shared-task line (DAGPap, Papilusion, etc.). They answer *"was
this text produced by an LLM?"* via token-distribution / stylometry.
*Limitation for our purpose:* style ≠ integrity. A perfect AI-text detector tells
you nothing about whether the experiments are consistent.

**B — AI-review detectors.** Work measuring and flagging LLM-generated *peer
reviews*. Important for venue integrity, but orthogonal to auditing the *paper*.

**C — Claim verification / rigor checkers.** The closest neighbors: general-purpose
claim-checking and rigor-scoring systems (e.g. FactReview-style claim
verification, RIGOURATE-style rigor dimensions), and citation-fabrication
taxonomies. They verify claims against the **world** and score rigor broadly.

## The gap (our wedge)

No existing line does **autoresearch-specific substantive-integrity forensics**,
which is the intersection of three things:

1. **Self-consistency forensics** — auditing the paper **against itself** (abstract
   ↔ tables ↔ body ↔ appendix; method-described ↔ method-evaluated; delta
   arithmetic). This needs **no external ground truth**, works PDF-only, and is the
   exact failure surface of machine-generated work. Cluster C checks claims against
   the world; it largely does not check the paper against itself.
2. **Fabrication forensics** specialized to pipeline failure modes — phantom
   results, fake/derived ground truth, self-normalized scores, missing/mistuned
   baselines, hallucinated and wrong-context citations.
3. **A curated, versioned hack-pattern taxonomy** maintained by people who build an
   autoresearch system (ARIS) and have seen these failures from the **generator's**
   side — encoded with detection signals *and* honest false-positive cases.

Plus two design choices that make the output trustworthy where generic "AI checks
AI" tools are dismissed: a **deterministic adjudicator** (the model never grades)
and **observability-aware severity** (you cannot assert code-level fraud from a
PDF). See `../references/`.

## What we deliberately do not claim

- We do not classify authorship. Provenance is out of scope by design.
- We do not reproduce experiments (no L3 in v0).
- We do not issue misconduct verdicts. Output is investigative support.

## Bibliography (to be populated by our own citation-forensics)

This section is intentionally left as named tool/work *families* rather than
hard-cited arXiv IDs until each entry is verified — dogfooding our own
`/citation-forensics` (existence + metadata + context) so this repo does not ship
the very thing it audits for: unverified citations. Contributions that add a
reference must pass `citation-forensics` first.
