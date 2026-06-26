# Contributing to Anti-Autoresearch

Thanks for helping make autoresearch papers *checkable*. **中文贡献者**:直接用中文开
issue / PR 完全没问题,下面的规则一样适用。

Anti-Autoresearch is a **reviewer-side integrity-forensics** toolkit — **not** an
AI-text detector. Every contribution has to keep that line: we surface *checkable
discrepancies* for a human to weigh. We never accuse, and we never guess "was this
written by AI".

## The #1 contribution we want: new hack-patterns

The [hack-pattern taxonomy](references/hack-pattern-taxonomy.md) is the heart of this
repo, and it grows with the community. If you've **seen a real autoresearch /
AI-Scientist paper pull a trick** that the current 39 patterns (7 families, A–G) don't
cover yet — that is the single most valuable thing you can send.

Two ways, pick whichever is less friction for you:

1. **Just report it** — open an issue titled `pattern: <short name>` with:
   - the concrete example (a paper, a table, a quoted sentence — redact identities if you need to),
   - *what's wrong* (the discrepancy a reviewer would catch), and
   - at what evidence tier it's decidable (PDF only? needs the LaTeX source? needs the repo + results?).

   We'll help shape it into a taxonomy entry.

2. **Send the PR** — add the pattern to `references/hack-pattern-taxonomy.md` under the
   right family, following the existing entry shape:

   ```markdown
   ### HP-YOUR-PATTERN — one-line, neutral description of the discrepancy
   - **level:** L0 (PDF) | L1 (+LaTeX source) | L2 (+repo/results) — the LOWEST tier at which it's decidable
   - **signals:** what a reviewer actually looks at to spot it
   - **fp_cases:** the legitimate situations that look the same (be honest — this is what stops it over-firing)
   - **severity_rule:** minor | major | critical, and when it escalates
   - **min_evidence:** the span(s) a finding must quote to stand
   ```

   A pattern PR should also add an **eval fixture** (see *Grow the taxonomy and the eval
   together* below) so the catalog can't silently rot.

## The honesty rules (every pattern + every flag must follow)

These are enforced in code (`tools/adjudicate_findings.py`) *and* in review — a PR that
breaks them won't merge:

1. **Discrepancy, not accusation.** Describe what doesn't line up and what a human should
   *check*. Never "fabricated", "faked", "reject", or "the authors lied".
2. **No authorship / provenance inference.** We do not claim a paper (or a hedge, or a
   placeholder array) was "written by AI". Flag the checkable artifact, not who produced
   it — that's exactly what keeps us out of the AI-text-detector trap.
3. **Observability-aware.** A finding declares the evidence tier it needs
   (`observability_level_required`); the adjudicator auto-demotes it on a run that
   couldn't see that much. You cannot shout "fraud" from a PDF.
4. **Anchored or it's nothing.** Every above-`info` finding must quote a **verbatim span**
   of a real evidence-ledger claim. No span → it fails closed to `info`.
5. **Surface signals stay capped.** Presentation / AI-flavor tells (family F) are *context
   only* — capped at `minor`, never a standalone verdict.
6. **The model proposes; it never grades.** Auditors emit findings; the deterministic
   adjudicator computes the verdict. Don't add a skill that judges itself. ("A loop can
   drive, never acquit.")

A signal a tool/model genuinely *can't* decide from the paper alone (e.g. "is this
trivial?" / "is this a duplicate?") goes in as an **`ADV-*` advisory pattern** —
memo-only, zero verdict weight.

## Grow the taxonomy and the eval together

A new pattern with no test is a claim we can't keep honest. When you add or change a
**deterministic** check, add a fixture under `eval/` (a clean case that must **not** fire
+ a corrupted case that **must**), and keep the gate green:

```bash
python3 eval/run_eval.py            # clean + corruption fixtures → all PASS, 0 false-positives
python3 tests/test_adjudicator.py   # adjudicator gate unit tests (the anti-slop invariants)
```

Semantic (LLM-layer) patterns don't need a deterministic detector, but they still need a
taxonomy entry with honest `fp_cases` and a `min_evidence` rule.

## Other welcome contributions

- **New auditor skills** — a fresh audit axis (`skills/<name>/SKILL.md` that reads the
  ledger and emits span-anchored findings). Wire it into the orchestrator and the
  `skill` enum in `schemas/finding.schema.json`.
- **Adjudicator gates** — new deterministic rules that make findings *harder* to
  over-claim (with a unit test in `tests/`).
- **Corruption fixtures** — more `eval/` cases, especially false-positive traps.
- **Bug reports** — a flag that over-fires on a *clean* paper is a real bug; show the
  paper + the spurious finding.

## Workflow

- Fork → branch → PR. Keep PRs focused (one pattern / one skill / one fix).
- Run `python3 eval/run_eval.py` and `python3 tests/test_adjudicator.py` before pushing —
  both must be green.
- In the PR, say *what discrepancy* your change catches and *at what observability tier*.

## Community

Questions, examples, or "is this already a known pattern?" — the WeChat group (shared with
the [ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) community) is
the fastest place. The QR is in the [README](README.md) (it rotates weekly; if it's
expired, open an issue and we'll post a fresh one).

By contributing, you agree your work is licensed under the repository's
[MIT License](LICENSE).
