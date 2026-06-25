# Integrity Forensics Contract

The wiring that makes the six skills a *pipeline* instead of six LLMs each reading
a PDF and inventing their own structure. Every skill obeys this contract.

## The pipeline

```
input (pdf | pdf+latex | pdf+repo+results)
        │
        ▼
[1] artifact manifest        tools/  → schemas/artifact_manifest.schema.json
        │   (derives observability level: L0/L1/L2)
        ▼
[2] evidence ledger          skills/evidence-ledger → schemas/claims.schema.json
        │   (deterministic span-anchored claims.json; the ONLY structure auditors read)
        ▼
[3] auditor skills (fan-out, each emits findings.json conforming to finding.schema)
        ├── consistency-audit          (flagship; intra-paper)
        ├── experiment-forensics       (repo present → integrity; PDF-only → risk signals)
        ├── baseline-comparison-audit  (missing/weak/mis-tuned baselines)
        ├── citation-forensics         (existence / metadata / context)
        └── adversarial-case-builder   (evidence-bound memo; emits NO verdict-bearing findings)
        │
        ▼
[4] deterministic adjudicator   tools/adjudicate_findings.py → schemas/report.schema.json
        │   (computes overall_verdict by RULES; LLM never grades)
        ▼
[5] human-facing report (REPORT.md + report.json + raw traces)
```

## Hard rules every skill must honor

1. **Read the ledger, not the raw paper, for structure.** A skill may re-open a
   source file to quote a span, but every finding's `evidence[].claim_id` must
   point at a ledger claim. No ledger claim → no finding.
2. **No span → no high severity.** A `critical` or `major` finding MUST have ≥1
   `evidence` entry with a non-empty `span`. The adjudicator demotes violators to
   `info`. (This is the single most important integrity rule of the repo.)
3. **Declare your observability requirement.** Every finding sets
   `observability_level_required`. Findings above the run's level are demoted (see
   `observability-levels.md`).
4. **Discrepancy, not accusation.** `description` and
   `recommended_reviewer_action` describe what to *check/ask*, never "reject" or
   "the authors faked X".
5. **Honest FP risk.** Set `false_positive_risk` truthfully. High-FP findings
   surface as notes, not flags.
6. **Hand off, don't overreach.** Claims you cannot settle internally ("SOTA",
   "first to…") get `verdict_local: needs_external_check` +
   `requires_external_check: true`, not a guess.
7. **Detect-only.** No skill ever edits the audited paper. This is a third-party
   forensics tool, not a co-author.
8. **Cross-model + reviewer≠adjudicator.** See `reviewer-independence.md`. The
   skill's LLM proposes; `tools/adjudicate_findings.py` decides.

## Output contract per skill

Each auditor writes, into the run's output dir:

- `<skill>.findings.json` — an array of objects conforming to
  `schemas/finding.schema.json`.
- `.aris/traces/<skill>/<date>_run<NN>/` — raw reviewer responses (forensic;
  never silently dropped), mirroring ARIS review-tracing.

The orchestrator (`workflows/anti-autoresearch`) concatenates all
`*.findings.json`, runs the adjudicator, and emits `REPORT.md` + `report.json`
(conforming to `schemas/report.schema.json`).

## Taxonomy is a mapping layer, not a detector

A finding MAY set `pattern_id` to map onto `hack-pattern-taxonomy.md`. The
taxonomy is applied **after** detection to name/cluster findings and to attach the
known false-positive cases for that pattern. Detection never starts from "go find
pattern HP-X"; it starts from the ledger + the checklist. This keeps the taxonomy
from degenerating into a brittle checklist adversaries route around.
