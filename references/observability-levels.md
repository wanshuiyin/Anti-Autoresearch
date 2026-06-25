# Observability Levels

The single most important honesty mechanism in Anti-Autoresearch.

A reviewer auditing an unknown submission rarely has everything. What you can
*decide* depends on what you can *see*. We make that explicit: every run declares
an **observability level**, and every finding declares the **minimum level at
which it is decidable**. The adjudicator (`tools/adjudicate_findings.py`)
**downgrades** any finding whose required level exceeds the run's actual level.

> You cannot assert code-level fraud from a PDF. You can only assert that the PDF
> contradicts itself, or that something checkable-from-text does not hold.

## The four levels

| Level | You have | You can decide | You CANNOT decide |
|------:|----------|----------------|-------------------|
| **L0** | PDF only | internal self-contradiction (abstract↔table↔body↔appendix), arithmetic errors (delta/aggregation), citation existence & wrong-context, scope-vs-evidence inside the text, missing-baseline *as stated*, absent variance/seeds | whether a reported number is *real*, GT provenance, code integrity, whether a "phantom" result was actually computed |
| **L1** | PDF + LaTeX/source | everything in L0, on **stable spans** (exact file:line, real table cells, real `.bib`), caption↔table at the source level | same as L0 — source ≠ execution |
| **L2** | PDF + repo + result files | everything above **plus** paper-number↔result-file match, fake ground truth, score self-normalization, dead/uncalled metric code, scope (N scenes/seeds actually run) | full reproduction (we do not re-run) |
| **L3** | repo + rerunnable environment | reproduction-class claims | — *v0 deliberately does not operate at L3; we never promise reproduction.* |

## Level derivation rule (deterministic)

```
present(repo) and present(results)      -> L2
present(latex) and not present(results) -> L1
only present(pdf)                        -> L0
```
(`tools/` implements exactly this; the manifest records the inputs, the rule
assigns the level.)

## Verdict vocabulary is level-aware

The report's `overall_verdict` is **never** "fabricated" / "honest". At L0–L1 the
strongest thing we can truthfully say is about *internal* integrity:

- `CLEAN_GIVEN_EVIDENCE` — no flags **at the available level**. This is **not**
  "the paper is honest"; it is "nothing checkable-at-this-level is broken".
- `SOFT_FLAGS` — minor / medium-or-high-FP-risk discrepancies a reviewer should ask about.
- `HARD_FLAGS` — ≥1 span-anchored **critical** discrepancy decidable at this level
  (e.g. abstract number contradicts its own table; a cited paper does not exist).

## How severity downgrade works

A finding tagged `observability_level_required: 2` (e.g. "result file does not
contain this number") emitted during an **L0** run is impossible to substantiate —
the adjudicator demotes it to at most `info` and counts it under
`counts.downgraded_for_observability`. This makes it structurally impossible to
shout "fraud" from a PDF.

## Why this matters

Existing claim-checkers tend to flatten everything into one confidence number.
That is exactly what makes "AI checks AI" feel like noise. By binding each verdict
to *what was observable*, the report stays defensible: a senior area chair can see
precisely which conclusions are load-bearing and which are "could not check".
