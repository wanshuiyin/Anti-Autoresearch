# Design notes

This repo's architecture was settled by a cross-model design review (the same
discipline the tool enforces): a draft design was put to an independent model
family (codex / gpt-5.5, xhigh) acting as a skeptical architect, and reshaped per
its critique. The four decisions below are the load-bearing ones.

## 1. Positioning: forensics, not detection
The verdict subject is **integrity under limited evidence**, not "is this paper
autoresearch?". Autoresearch is the **failure-prior / taxonomy**, never the thing
being detected. Making "AI-generated" the verdict would collapse the tool into an
AI-text classifier (cluster A) and invite exactly the dismissal we want to avoid.

## 2. The evidence ledger is the spine
Five LLM auditors each parsing a PDF = five hallucinated structures. So a single
**deterministic** pass produces `claims.json` (span-anchored, hashed), and it is
the *only* structure auditors reason over. Invariant: **no span → no high-severity
finding.** This is the difference between "a model said so" and "here is the exact
sentence and its hash".

## 3. The LLM never grades (reviewer ≠ adjudicator)
The structural answer to "LLM slop grading LLM slop": auditors *propose* findings;
`tools/adjudicate_findings.py` *decides* the verdict by fixed rules (span gate →
observability gate → FP-risk cap → memo-only cap). The verdict is reproducible with
no model in the final decision. This is a second independence axis on top of ARIS's
cross-model (executor ≠ reviewer) rule.

## 4. Observability levels make honesty structural
A run cannot assert what it cannot see. Each finding declares the minimum level it
needs; the adjudicator demotes findings above the run's level. A PDF-only run
*cannot* emit a code-fraud verdict — it is demoted to an info "could-not-verify"
signal. Verdict vocabulary is `CLEAN_GIVEN_EVIDENCE / SOFT_FLAGS / HARD_FLAGS`,
deliberately not "honest / fabricated".

## Consequence: the eval harness is not optional
Because the deterministic spine makes concrete, checkable claims, it can be
*tested*. `eval/` injects known defects into a clean fixture and asserts they are
caught (recall) while the clean fixture stays clean (false positives). Without this
the project would be just-another-LLM-checker; with it, every change is measured.

## Build order (v0 critical path)
1. schemas + evidence ledger + ingest
2. deterministic consistency checks + adjudicator + observability levels
3. eval fixtures (clean + synthetic corruptions) + harness  ← credibility gate
4. citation-forensics (high-value, independently defensible)
5. experiment-forensics (L2 mode)
6. baseline-comparison-audit (small domain profile first)
7. hack-pattern taxonomy mapped only to evidence-backed signals
8. adversarial-case-builder (memo synthesis only, never a verdict source)

## Deliberate non-goals (v0)
Authorship classification · experiment reproduction (no L3) · misconduct verdicts ·
auto-editing the audited paper. All four are out of scope by design, not by
omission.
