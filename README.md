# Anti-Autoresearch

**Substantive integrity-forensics for research papers — especially machine-generated
(autoresearch / AI-Scientist-style) output.**

> Regardless of *who or what* wrote a paper, does the science hold together and
> reflect its own evidence? Anti-Autoresearch audits a submission for
> **self-consistency** and **fabrication**, and produces a span-anchored,
> reviewer-ready report. It is **not** an AI-text detector, and it does **not**
> judge misconduct — it surfaces discrepancies a human reviewer should investigate.

中文版见 [README_CN.md](README_CN.md). Built on the audit DNA of
[ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) — by the
people who watch these failure modes from the *generator's* side.

---

## Why this exists

Machine-generated papers and reviews are now a measurable share of the literature,
and the failure that matters for an area chair is rarely *"was this text written by
an LLM?"* (a human can write a dishonest paper; an LLM can write an honest one). It
is: **does the paper contradict itself, and is it backed by its own evidence?**

That is what autoresearch pipelines get wrong — they hallucinate *local* coherence:
an abstract number that no table reports, a "16% improvement" that the operands say
is 6%, a citation for a claim the cited paper never makes, a method described one
way and evaluated another. Those are checkable. This repo checks them.

## What it is — and is not

| | |
|---|---|
| ✅ **is** | self-consistency + fabrication forensics; evidence-ledger-anchored; observability-aware; reviewer/AC decision support |
| ❌ **is not** | an AI-text classifier (Pangram / GPTZero / Binoculars), an AI-review detector, a misconduct verdict, or a co-author that edits the paper |

### The gap it fills

Existing work clusters into (A) **AI-text detectors** — stylometry, "is it
LLM-written"; (B) **AI-review detectors**; (C) **general claim/rigor checkers**
(FactReview, RIGOURATE, citation-fabrication taxonomies). None do
**autoresearch-specific substantive-integrity forensics**: internal-consistency
forensics *plus* a curated taxonomy of the *specific* hack-patterns that
LLM-driven research pipelines produce. We verify the paper **against itself** (no
external ground truth needed — exactly where machine output cracks) and specialize
the failure catalog to autoresearch. See [docs/positioning.md](docs/positioning.md).

## Status — what v0 actually ships

Being precise about what runs today vs what is an agent-orchestrated contract
(this distinction is the point — see [DESIGN.md](DESIGN.md)):

- **Deterministic core — runs now, zero-dependency, tested.** The evidence-ledger
  extractor, the artifact-manifest / observability derivation, the numeric
  self-consistency checks (`HP-DELTA-ERROR`, `HP-NUM-INFLATE`), and the rule-based
  adjudicator. The `eval/` harness gates these: **100% recall on the two
  deterministic numeric patterns** across the bundled fixtures, **zero clean
  false-positives**, every above-info finding ledger-anchored. This is the
  load-bearing, reproducible part — no model in the loop.
- **Agent-layer audits — alpha, require Claude + a cross-model reviewer.** The
  *semantic* skills (method-drift, ablation attribution, wrong-context citation,
  baseline adequacy, experiment-code integrity) are `SKILL.md` contracts run by an
  agent via `/anti-autoresearch`. They propose span-anchored findings that the
  *same* deterministic adjudicator scores; they are not yet covered by the
  deterministic eval (semantic judgments can't be unit-tested the same way).

The **verdict machinery and the numeric core are real and tested**; semantic
coverage is an agent contract that grows as the taxonomy and eval grow. The
headline "fabrication forensics" is the *roadmap*, honestly scoped here.

## How it stays honest (the anti-"LLM-slop" design)

The obvious dismissal of any such tool is *"an LLM grading another LLM's paper is
just noise."* Three structural defenses, not just a disclaimer:

1. **Evidence ledger.** One deterministic pass turns the paper into `claims.json` —
   span-anchored, hashed claims. Every finding must cite a `claim_id` + verbatim
   span. **No span → it cannot be a high-severity finding.**
2. **The LLM never grades.** Auditors *propose* findings; a **deterministic
   adjudicator** (`tools/adjudicate_findings.py`, pure rules) computes the verdict.
   Same findings → same verdict, with no model in the final decision.
3. **Observability levels.** A run declares what it could see (L0 PDF-only → L2
   repo+results); findings that need code are **auto-demoted** on a PDF-only run.
   You can never shout "fraud" from a PDF. See
   [references/observability-levels.md](references/observability-levels.md).

And an **eval harness** (`eval/`) proves the deterministic core on clean +
synthetically-corrupted fixtures every change — measured false-positive / recall,
not vibes.

## Quickstart

The deterministic core runs with **zero dependencies** (Python 3 stdlib):

```bash
# 1) Prove the pipeline on clean + corrupted fixtures (the regression gate)
python3 eval/run_eval.py
#   clean            CLEAN_GIVEN_EVIDENCE   PASS
#   delta_inflate    SOFT_FLAGS             PASS   caught=HP-DELTA-ERROR
#   headline_inflate SOFT_FLAGS             PASS   caught=HP-NUM-INFLATE
#   injected-defect recall: 100% (2 deterministic numeric patterns) · clean FP: none

# 1b) gate unit tests (the anti-slop guarantee)
python3 tests/test_adjudicator.py

# 2) Build an evidence ledger from a real paper's LaTeX
python3 tools/build_claim_ledger.py --paper-id mypaper \
    --latex main.tex sections/*.tex --observability-level 1 --out claims.json

# 3) Run the deterministic consistency checks
python3 tools/check_numeric_consistency.py --ledger claims.json --out findings.json

# 4) Adjudicate into a report (deterministic verdict)
python3 tools/adjudicate_findings.py --findings findings.json \
    --paper-id mypaper --observability-level 1 --out report.json --md REPORT.md
```

For the **full** sweep (adds the cross-model semantic audits via Claude + codex),
run the agent workflow `/anti-autoresearch <paper-dir>` — see
[workflows/anti-autoresearch/SKILL.md](workflows/anti-autoresearch/SKILL.md). The
skills follow the [Claude Code / ARIS skill](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)
convention.

## Architecture

```
input (pdf | pdf+latex | pdf+repo+results)
   │
   ▼  [evidence-ledger]  artifact_manifest.json (+ observability level) + claims.json   ← deterministic
   │
   ▼  fan out auditors (each reads the ledger, emits span-anchored findings):
        consistency-audit          flagship · paper vs itself · ARIS paper-claim-audit
        citation-forensics         exists? correct? right context? · ARIS citation-audit
        baseline-comparison-audit  missing/weak/mistuned baselines · ARIS paper-claim-audit
        experiment-forensics       L2: fake GT / self-norm / phantom · ARIS experiment-audit
        adversarial-case-builder   evidence-bound memo, no verdict · ARIS kill-argument
   │
   ▼  [adjudicate_findings.py]  rules, not a model → REPORT.md + report.json            ← deterministic
```

| Path | What |
|------|------|
| `skills/` | the six auditor skills (LLM proposes findings, span-anchored) |
| `workflows/anti-autoresearch/` | the end-to-end orchestrator |
| `tools/` | deterministic spine: manifest/observability derivation · ledger builder · numeric checks · adjudicator |
| `schemas/` | JSON contracts: claims · finding · report · artifact manifest |
| `references/` | hack-pattern taxonomy (the IP) · observability levels · reviewer independence · forensics contract |
| `eval/` | clean + synthetic-corruption fixtures + the regression harness |
| `tests/` | gate unit tests for the adjudicator (the anti-slop invariants) |
| `docs/` | positioning vs existing work · limitations |

## Honest limitations

- **Forensics ≠ proof of misconduct.** Output is *flags for a human*, never an accusation.
- **PDF-only (L0) catches inconsistency + tells, not all fabrication** — it cannot
  verify external ground truth or run code.
- **False positives exist** (legitimate round numbers, single-seed pilots,
  deliberate scope choices). Hence tiers, FP-risk tags, and the eval harness — not
  a binary "guilty".
- **The taxonomy is a living document.** Adversaries who know a signal can route
  around it; this is a safety net, not a guarantee. See [docs/limitations.md](docs/limitations.md).

## Relationship to ARIS

ARIS is an autoresearch *system*. Anti-Autoresearch is its adversarial sibling: it
reuses and adapts ARIS's audit skills (`experiment-audit`, `paper-claim-audit`,
`citation-audit`, `kill-argument`) and the cross-model review discipline, but
reframes them for a **third party auditing an unknown submission** rather than an
author checking their own work. The moat is exactly that inside knowledge of how
generators fail.

## License

MIT — see [LICENSE](LICENSE).
