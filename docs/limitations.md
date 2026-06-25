# Limitations & failure modes (read before trusting any report)

Anti-Autoresearch is a **safety net for a human reviewer**, not an oracle. Where it
can be wrong:

## It does not prove misconduct
Every finding is a *discrepancy to investigate*. An honest paper can trip a signal
(legitimate "best config" numbers, deliberate single-seed pilots, conscious scope
choices). The report's verdict vocabulary is `CLEAN_GIVEN_EVIDENCE / SOFT_FLAGS /
HARD_FLAGS` — never "fabricated / honest". `human_review_required` is always true.

## Observability bounds what is decidable
- **L0 (PDF-only):** internal contradictions, arithmetic, citation existence/
  context, scope-vs-text. It **cannot** verify a number is real, GT provenance, or
  any code behaviour. Code-level patterns appear only as info "could-not-verify".
- **L1 (+ source):** the same, on stable spans.
- **L2 (+ repo + results):** adds paper↔result-file matching and eval-code
  integrity. Still does **not** reproduce.
- There is no **L3** in v0 — we never claim reproduction.

## False positives are real and measured
The deterministic checks are tuned conservatively and the high-FP ones (e.g.
"headline number not in any table") are capped in severity. The `eval/` harness
exists precisely to measure FP/recall on every change; a pattern that fires with
high FP is demoted, not shipped silently. Numbers in `eval/` are the honest record.

## Extraction is imperfect
The ledger extractor is regex/structure-based. PDF-extracted text is tagged
`confidence: low`. Exotic LaTeX, image-only tables, and unusual number formats can
be missed (false negatives) — coverage is honest, not total.

## The taxonomy can be gamed
It is a *living, versioned* document. An author who knows a specific signal can
route around it. The taxonomy_version is stamped into every report so findings stay
interpretable as it evolves, but it is a moving target, not a proof system.

## The model layer can still err
The semantic audits use a cross-model reviewer (different family from the
executor). That reduces, but does not eliminate, model error. The structural
guard is that the model **proposes**, the deterministic adjudicator **decides**,
and unanchored findings are dropped — so a model hallucination cannot, by itself,
raise the verdict.

## Intended use
Reviewer / area-chair triage; author self-check before submission; meta-science
auditing of corpora. **Not** for public accusation, automated desk-reject, or any
decision without a human in the loop.
