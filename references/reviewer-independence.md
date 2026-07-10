# Reviewer Independence (two layers)

Anti-Autoresearch inherits ARIS's cross-model adversarial-review discipline and
adds a second independence axis that is specific to a *forensics* tool.

## Layer 1 — Cross-model (executor ≠ reviewer)

The agent orchestrating the audit (the **executor**, typically Claude) must not be
the model that **judges** integrity. The executor:

- builds the artifact manifest and the evidence ledger,
- collects file paths and ledger `claim_id`s,
- passes **paths + the ledger + the checklist** to the reviewer.

The reviewer is a **different model family** (default: codex / gpt-5.6-sol at xhigh
reasoning, fresh threads). The reviewer reads the artifacts directly and proposes
findings. The executor does **not** summarize, pre-judge, or leak its own opinion
into the reviewer prompt — only structured inputs (the same rule as ARIS
`shared-references/reviewer-independence.md`).

Fresh thread per audit dimension (no `codex-reply` carrying one dimension's
conclusions into another) — this is the bias guard.

## Capability fallback (capability errors only — the same contract as ARIS)

Pin `model: gpt-5.6-sol` + `config: {"model_reasoning_effort": "xhigh"}` explicitly in
every fresh reviewer call (do not rely on `~/.codex/config.toml`; the catalog default
effort for gpt-5.6-sol is `low`). If — and only if — the call fails with an error that
**explicitly identifies the requested effort as unsupported** (codex-cli < 0.144.1) or
**`gpt-5.6-sol` as unknown/unavailable to this account**, retry `gpt-5.5` + `xhigh`.
NEVER step down on timeout, rate-limit, auth, transport, or server errors (a blind
retry risks double-running a review). Never run an auditor below `xhigh`. If no allowed
pair succeeds, record the dimension as `review_unavailable` in the run's
`coverage.json` — the adjudicator then refuses to issue a CLEAN verdict for an
incomplete sweep. Findings and traces record the pair that **actually ran** (the
resolved pair), never the target default.

## Layer 2 — Reviewer ≠ adjudicator (NEW, the anti-slop axis)

This is the structural defense against the obvious dismissal — *"an LLM grading
another LLM's paper is just slop."*

**The LLM reviewer never renders the final verdict.** It emits **findings**
(`schemas/finding.schema.json`), each anchored to a ledger span and an artifact
hash. The **overall verdict is computed by deterministic code**
(`tools/adjudicate_findings.py`) from the full finding set, by fixed rules:

```
HARD_FLAGS  if any finding is severity=critical, span-anchored, and decidable
            at the run's observability level
SOFT_FLAGS  else if any major/minor finding survives FP-risk + observability gates
CLEAN_GIVEN_EVIDENCE otherwise
```

The LLM is demoted from **judge** to **evidence-extractor / candidate-explainer**.
Its job is to *find and quote*; the rules *decide*. Two consequences:

1. A finding with no span cannot raise the verdict (the adjudicator rejects
   critical/major findings that lack evidence — see the contract).
2. The verdict is reproducible: same ledger + same findings → same verdict, with
   no model in the final decision.

## What the reviewer is told (and not told)

- **Told:** the artifact paths, the evidence ledger, the per-dimension checklist,
  the observability level.
- **Not told:** any prior dimension's findings, the executor's hunches, or "this
  paper is probably AI-generated". The tool is agnostic to authorship; it audits
  integrity, not provenance.

## Honesty obligations on the reviewer

- Describe a **discrepancy or risk**, never an accusation of misconduct.
- Self-report `false_positive_risk` honestly (legit round numbers, legit
  single-seed pilots, deliberate scope choices are common FPs).
- Tag `requires_external_check: true` for claims ("first", "SOTA") that internal
  consistency cannot settle — hand them to baseline / citation forensics rather
  than ruling.
