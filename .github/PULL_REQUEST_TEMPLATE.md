<!-- Thanks for contributing! Keep PRs focused (one pattern / one skill / one fix). -->

## What discrepancy does this catch / fix?
<!-- One line, in reviewer-facing terms — a checkable discrepancy, not an accusation. -->

## Observability tier
<!-- L0 (PDF) · L1 (+LaTeX) · L2 (+repo/results) · needs external lookup -->

## Checklist
- [ ] `python3 tests/test_adjudicator.py` is green
- [ ] `python3 eval/run_eval.py` is green (100% recall · 0 clean false-positives)
- [ ] A new/changed **deterministic** check has an `eval/` fixture (a clean case that must NOT fire + a corrupt case that MUST)
- [ ] Honesty rules followed: discrepancy not accusation · no authorship/provenance inference · span-anchored · observability-aware
- [ ] If a new pattern: taxonomy entry added (`level` / `signals` / `fp_cases` / `severity_rule` / `min_evidence`) + provenance/ack line if adapted from prior work
