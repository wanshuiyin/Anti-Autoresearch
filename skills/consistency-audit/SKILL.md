---
name: consistency-audit
description: "Flagship intra-paper self-consistency forensics: does the paper contradict ITSELF across abstract/tables/body/appendix, and does the method described match the method evaluated? Needs no external ground truth — works PDF-only (L0). Runs deterministic arithmetic checks + a cross-model semantic pass, all span-anchored to the evidence ledger. Triggers: \"consistency audit\", \"check the paper against itself\", \"self-consistency\", \"内部自洽\"."
argument-hint: [paper-dir | claims.json]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, mcp__codex__codex, mcp__codex__codex-reply
---

# Consistency Audit — the paper vs itself

> The flagship instrument. Internal contradiction is the single most defensible
> thing you can check on an unknown submission: it needs no external GT, works at
> L0 (PDF-only), and is exactly where machine-generated papers crack (they
> hallucinate *local* coherence). Adapted from ARIS `paper-claim-audit`, reframed
> from "paper vs result files" to "paper vs itself".

Audit internal consistency for: **$ARGUMENTS** (requires `claims.json` from
`/evidence-ledger`).

## Step 1 — Deterministic arithmetic checks (no LLM)

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
python3 "$ROOT/tools/check_numeric_consistency.py" --ledger claims.json \
    --out consistency-audit.deterministic.findings.json
```

Catches `HP-DELTA-ERROR` (stated improvement ≠ operand arithmetic) and
`HP-NUM-INFLATE` (headline number absent from every table). These are reproducible
and form the eval backbone — they run before any model.

## Step 2 — Cross-model semantic pass (reviewer ≠ adjudicator)

The arithmetic layer cannot see *meaning* drift. Send the ledger + the source
paths to a fresh `mcp__codex__codex` (gpt-5.5, xhigh, `sandbox: read-only`, `cwd` =
paper dir). The reviewer PROPOSES findings; it does not grade the paper (the
deterministic adjudicator does). Use this checklist (one fresh thread):

```
You are an integrity-forensics reviewer. You are given an evidence ledger
(claims.json) and the paper source. For EACH item below, find concrete
contradictions and output findings. Every finding MUST cite a claim_id and quote
the exact span(s). If you cannot cite a span, do not raise the finding above info.
Describe a DISCREPANCY to investigate — never accuse of misconduct.

Checklist (map each to a pattern_id from references/hack-pattern-taxonomy.md):
  1. number coherence  : same metric+setting with different values across
                         abstract / body / table / appendix.            [HP-NUM-INFLATE, HP-APPENDIX-CONTRA]
  2. metric direction/unit: %-vs-points, higher/lower-better confusion.  [HP-UNIT-DIR-MISMATCH]
  3. aggregation       : "mean of N seeds" but value = best seed; N drift.[HP-AGG-DRIFT]
  4. denominator drift : tables averaging different populations conflated.[HP-DENOM-DRIFT]
  5. method identity   : method DESCRIBED ≠ method EVALUATED (A vs A-lite,
                         A+oracle, extra data, different backbone).       [HP-METHOD-DRIFT]
  6. ablation attribution: gain credited to X but no ablation isolates X. [HP-ABLATION-ATTRIB]
  7. caption vs content: caption describes what the table/figure doesn't. [HP-CAPTION-MISMATCH]
  8. scope vs evidence : "comprehensive/robust/general" on thin scope.    [HP-SCOPE-INFLATE]
  9. theorem scope     : abstract general, theorem only under strong/unstated
                         assumptions.                                     [HP-THEOREM-SCOPE-DRIFT]
 10. external claims   : "first / SOTA" — DO NOT rule; emit verdict_local
                         needs_external_check + requires_external_check.

For each finding output JSON conforming to schemas/finding.schema.json:
  {finding_id, skill:"consistency-audit", pattern_id, title, description,
   severity, observability_level_required, evidence:[{claim_id, span, location}],
   verdict_local, false_positive_risk, recommended_reviewer_action}
Set false_positive_risk honestly (legit "best config" labels, deliberate scope
choices, standard rounding are common FPs).
```

## Step 3 — Validate + merge

The executor (Claude) validates every reviewer finding **before** keeping it:

- the `claim_id` exists in `claims.json`;
- the quoted `span` is a verbatim substring of the cited claim's `text_span`
  (reject paraphrases — this is the anti-hallucination gate);
- `observability_level_required` is set.

Write the surviving findings to `consistency-audit.findings.json` (merge with the
deterministic findings from Step 1). Do **not** compute a verdict here.

## Step 4 — Trace

Save the raw reviewer response under `.aris/traces/consistency-audit/<date>_run<NN>/`
(forensic; never silently dropped).

## Key rules

- **No span → no high severity.** Enforced again by the adjudicator, but reject
  unanchored findings here first.
- **Discrepancy, not accusation.** Output asks a reviewer to *check*, never to reject.
- **Hand off external claims.** "SOTA/first" go to baseline / citation forensics.
- **Detect-only.** Never edit the audited paper.
