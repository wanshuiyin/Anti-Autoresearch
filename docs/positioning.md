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
you nothing about whether the experiments are consistent — and the bias runs the
other way too: Liang et al. (2023, *Patterns*; arXiv:2304.02819) found GPT detectors
misclassified **>60% of non-native-English TOEFL essays** as AI-written. Stylometry
penalizes a writing register, not dishonesty. This is exactly why every surface /
AI-flavor signal in this repo is high-false-positive context (taxonomy family F,
capped at `minor`), never a verdict.

**B — AI-review detectors.** Work measuring and flagging LLM-generated *peer
reviews*. Important for venue integrity, but orthogonal to auditing the *paper*.

**C — Self-consistency & rigor / claim checkers.** The closest neighbors — and the
comparison we have to make honestly, because *checking a paper against itself is not
new*. It splits two ways:

- *Deterministic but narrow.* statcheck (Nuijten & Epskamp) recomputes reported NHST
  *p*-values from their own test statistics; GRIM / GRIMMER (Brown & Heathers; Anaya)
  test whether reported means/SDs are arithmetically possible for the stated N. These
  *do* check the paper against itself, deterministically — but over one narrow surface
  (psychology-style NHST and integer-item means).
- *Broad but LLM-scored.* RIGOURATE (arXiv:2601.04350) scores whether a paper's stated
  conclusions overstate its **own** evidence — paper-against-itself, and broad — but it
  is a single model-produced overstatement score, with the LLM itself doing the grading.
- *Framing-adjacent.* FactReview (arXiv:2604.04074) shares our identity — it audits a
  paper's empirical claims and explicitly **does not make accept/reject decisions** —
  but it grounds claims against the **external literature** and **executes the paper's
  repository** to re-derive results (an L3 reproduction move we deliberately refuse),
  it is LLM-judged, and it has no hack-pattern taxonomy and no observability tiers.

Plus citation-fabrication taxonomies (e.g. Ansari) cataloguing hallucinated /
wrong-context references.

## The gap (our wedge)

No existing line does **autoresearch-specific substantive-integrity forensics**,
which is the intersection of three things:

1. **Breadth of self-consistency forensics** — auditing the paper **against itself**
   (abstract ↔ tables ↔ body ↔ appendix; method-described ↔ method-evaluated; delta
   arithmetic). This needs **no external ground truth**, works PDF-only, and is the
   exact failure surface of machine-generated work. Paper-against-itself checking is
   *not* new, but prior work is either deterministic-but-narrow (statcheck/GRIM: one
   psychology NHST / means surface) or broad-but-LLM-scored (RIGOURATE: a single
   model-graded overstatement number). Our edge here is the **breadth** of the check —
   across all eight taxonomy families — paired with the deterministic adjudicator and
   observability tiers below.
2. **Fabrication forensics** specialized to pipeline failure modes — phantom
   results, fake/derived ground truth, self-normalized scores, missing/mistuned
   baselines, hallucinated and wrong-context citations.
3. **A curated, versioned hack-pattern taxonomy** maintained by people who build an
   autoresearch system (ARIS) and have seen these failures from the **generator's**
   side — encoded with detection signals *and* honest false-positive cases.

Plus two design choices that make the output trustworthy where generic "AI checks
AI" tools are dismissed: a **deterministic adjudicator** (the model never grades)
and **observability-aware severity** (you cannot assert code-level fraud from a
PDF). See `../references/`. In one line, the wedge is the *combination* — breadth of
self-consistency × a deterministic adjudicator × observability tiers × an
autoresearch-specific hack-pattern taxonomy — which no single neighbor (statcheck,
GRIM, RIGOURATE, FactReview) offers.

## What we deliberately do not claim

- We do not classify authorship. Provenance is out of scope by design.
- We do not reproduce experiments (no L3 in v0).
- We do not issue misconduct verdicts. Output is investigative support.

## Bibliography

We dogfood our own `/citation-forensics` (existence + metadata + context) before any
entry is hard-cited, so this repo does not ship the very thing it audits for. The
entries below were checked that way (existence + title + topic verified); the rest of
the landscape (statcheck, GRIM/GRIMMER, FactReview's non-arXiv tooling,
citation-fabrication taxonomies) is credited by name in the README's *Prior art &
acknowledgments*. Contributions that add a reference must pass `citation-forensics` first.

- RIGOURATE — *Quantifying Scientific Exaggeration with Evidence-Aligned Claim Evaluation* (James, Xiao, Li, Moosavi, Lin). Conclusion-vs-own-evidence overstatement scoring. arXiv:2601.04350.
- FactReview — *Evidence-Grounded Peer Review with Execution-Based Claim Verification* (Yue, Ouyang, et al.). Audits empirical claims without accept/reject decisions; grounds against external literature + executes the repo (an L3 move we refuse). arXiv:2604.04074.
- Liang et al. (2023). *GPT detectors are biased against non-native English writers.* Patterns. arXiv:2304.02819.
- ARIS — the parent system Anti-Autoresearch is derived from. arXiv:2605.03042.
