# Anti-Autoresearch 🛡️

**Substantive integrity-forensics for research papers — especially machine-generated
(autoresearch / AI-Scientist-style) output.**

> **The dual of [ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)** — the ~12.5k★ autoresearch agent platform. ARIS is built to do autoresearch *responsibly*: it ships a multi-layer audit stack (experiment-integrity · result-to-claim · zero-context paper-claim audit · citation audit) so its **own** output stays honest. **Anti-Autoresearch is the other side of that coin** — the reviewer-side tool that catches autoresearch produced *without* those guardrails. Same audit DNA, pointed outward. (中文 [README_CN.md](README_CN.md) · ARIS provenance below)

> Regardless of *who or what* wrote a paper, does the science hold together and
> reflect its own evidence? Anti-Autoresearch audits a submission for
> **self-consistency** and **fabrication**, and produces a span-anchored,
> reviewer-ready report. It is **not** an AI-text detector, and it does **not**
> judge misconduct — it surfaces discrepancies a human reviewer should investigate.

---

## 🚀 Quickstart

### Agent workflow (normal use)

Anti-Autoresearch runs as a Claude Code skill workflow — the Python tools are the
deterministic spine *inside* that workflow, not the usual interface.

```bash
# 1) Install the skills + workflow (global, or pass a project's .claude/skills dir)
git clone https://github.com/wanshuiyin/Anti-Autoresearch.git
./Anti-Autoresearch/tools/install_anti_autoresearch.sh              # → ~/.claude/skills
# project-local instead: ./Anti-Autoresearch/tools/install_anti_autoresearch.sh ./.claude/skills

# 2) Wire the cross-model reviewer (end state: Claude Code exposes mcp__codex__codex)
claude mcp add codex -- codex mcp-server
claude mcp list

# 3) Audit a paper
claude
> /anti-autoresearch ~/papers/submission
```

The run writes `REPORT.md` + `report.json` + `claims.json` + per-skill
`*.findings.json` into the paper directory. Put the code/result artifacts alongside
the paper to unlock L2 checks; PDF/source-only runs are observability-limited by
design.

### Deterministic core (CI / offline / zero-dependency)

This bypasses the agent layer and exercises only the eval-tested deterministic
checks — use it for CI, regression tests, or environments with no cross-model
reviewer (Python 3 stdlib, nothing to install):

```bash
# Prove the pipeline on clean + corrupted fixtures (the regression gate)
python3 eval/run_eval.py
#   clean / delta_inflate / dup_table / headline_inflate  → all PASS
#   injected-defect recall: 100% (3 deterministic patterns) · clean FP: none
python3 tests/test_adjudicator.py        # gate unit tests (the anti-slop guarantee)

# Or run the spine by hand on a real paper:
python3 tools/build_claim_ledger.py --paper-id mypaper --latex main.tex sections/*.tex \
    --observability-level 1 --out claims.json
python3 tools/check_numeric_consistency.py --ledger claims.json --out findings.json
python3 tools/adjudicate_findings.py --findings findings.json --ledger claims.json \
    --paper-id mypaper --observability-level 1 --out report.json --md REPORT.md
#   --ledger is REQUIRED: a finding must quote a verbatim ledger span or it fails closed to info.
```

## 🎯 Why this exists

Machine-generated papers and reviews are now a measurable share of the literature,
and the failure that matters for an area chair is rarely *"was this text written by
an LLM?"* (a human can write a dishonest paper; an LLM can write an honest one). It
is: **does the paper contradict itself, and is it backed by its own evidence?**

That is what autoresearch pipelines get wrong — they hallucinate *local* coherence:
an abstract number that no table reports, a "16% improvement" that the operands say
is 6%, a citation for a claim the cited paper never makes, a method described one
way and evaluated another.

Those are checkable under a declared observability level. Concretely, taxonomy v0.2
names **27 hack-patterns across 6 families** (numeric self-consistency · method /
scope · baseline integrity · experiment integrity · citation integrity ·
presentation / surface signals) — the repo's **coverage vocabulary**, not a
27-detector benchmark.

> **Shipped v0:** the deterministic spine and the three ✓ patterns below are
> eval-tested; the other 24 are agent-layer contracts (a cross-model reviewer
> proposes span-anchored findings, the deterministic adjudicator scores or demotes
> them) — not bundled-eval detector claims.

The full catalog, with detection signals and false-positive cases, lives in
[the taxonomy](references/hack-pattern-taxonomy.md). A representative ten (✓ = gated
by the deterministic eval today):

- `HP-NUM-INFLATE` — abstract says 85.3%, but Table 2 never gets past 84.7%. ✓
- `HP-DELTA-ERROR` — a "16% improvement" from 73.1 to 78.0 is really 6.7%. ✓
- `HP-DUP-TABLE` — two tables carry the identical ordered numbers — usually copy-paste padding. ✓
- `HP-METHOD-DRIFT` — the method section says "no labels"; the eval quietly uses gold-label calibration.
- `HP-SCOPE-INFLATE` — "comprehensive" turns out to be two datasets, one domain, maybe one seed.
- `HP-MISSING-BASELINE` — SOTA is claimed while the obvious recent baseline never appears in the table.
- `HP-FAKE-GT` — (L2) the "reference" targets are model outputs, then reported as ground truth.
- `HP-PHANTOM-RESULT` — (L2) a headline number points at a result file or metric key that isn't there.
- `HP-SUSPICIOUS-REGULARITY` — (L2) rows differ by a suspiciously clean offset — check the files before calling it fake.
- `HP-CITE-HALLUC` — the DOI / arXiv id / venue / author list simply doesn't exist.

<details>
<summary><b>… the other 17, listed in full (across all 6 families)</b></summary>

**A · Numeric self-consistency**
- `HP-AGG-DRIFT` — they write "mean over seeds", but the number is really the best seed.
- `HP-DENOM-DRIFT` — one table averages all tasks; the conclusion quietly uses the applicable-only subset.
- `HP-UNIT-DIR-MISMATCH` — points silently become percent, or a lower-better metric is celebrated upward.
- `HP-CAPTION-MISMATCH` — the caption promises N=5 and method B; the plot shows neither.
- `HP-APPENDIX-CONTRA` — the appendix reruns the same quantity and disagrees with the main text.

**B · Method & scope**
- `HP-ABLATION-ATTRIB` — they credit component X, but every ablation keeps X bundled with Y.
- `HP-THEOREM-SCOPE-DRIFT` — the abstract sells a general theorem; the assumptions do nearly all the work.

**C · Baseline integrity**
- `HP-WEAK-BASELINE` — the new method gets tuning and compute the baseline plainly did not.
- `HP-SIG-OVERLAP` — "outperforms" by crumbs, with overlapping error bars or no seeds shown.

**D · Experiment integrity** (needs code/results — L2)
- `HP-SELF-NORM` — (L2) the score nears 1.0 because it's divided by the model's own max.
- `HP-DEAD-METRIC` — (L2) a metric function exists with no call site and no result, yet is discussed.

**E · Citation integrity**
- `HP-CITE-CONTEXT` — real paper, wrong job: cited for a claim it explicitly doesn't make.

**F · Presentation & surface signals** (capped at `minor` — never a verdict)
- `HP-THIN-FLOAT` — a "broad empirical study" somehow has two tables and one lonely figure.
- `HP-LLM-FIGURE` — the "figure" is decorative model art, not a plot or a real diagram.
- `HP-PAGE-PADDING` — oversized floats, repeated text, or empty prose doing page-count labor.
- `HP-JARGON-STUFF` — dense buzzwords pile up while the surrounding argument adds almost nothing.
- `HP-AI-FLAVOR` — boilerplate transitions and identical paragraph rhythms; context, not evidence.

</details>

**This is not hypothetical.** Paraphrased from a public reviewer account during the
NeurIPS 2026 cycle (illustrative, not a citation), one batch maps almost one-to-one
onto the taxonomy this repo encodes:

> - *Paper 1* — "data tables don't match the text; several rows are misaligned;
>   there's an obvious add/subtract regularity across backbones — it doesn't look
>   like it was actually run." → consistency · `HP-SUSPICIOUS-REGULARITY`
> - *Paper 2* — "two tables fill a page and are identical; the one figure is
>   LLM-generated; and it *still* didn't fill 9 pages." → `HP-DUP-TABLE` ·
>   presentation signals
> - *Paper 3* — "formula derivations don't hold; the experiments look complete but
>   the math can't give those results." → claim-vs-derivation
> - *Paper 4* — "open-sourced, beautifully written and drawn — but I ran the code
>   and it gives completely different results from the paper." → experiment-forensics (L2)

The fourth case is this repo's thesis in one line: **surface polish is not integrity.**

## 🔒 How it stays honest (the anti-"LLM-slop" design)

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

**Surface / AI-flavor signals have a separate firewall.** AI-flavor prose, duplicate
tables, LLM-generated figures, and page-padding are reported only as
*high-false-positive context*: the adjudicator hard-caps `presentation-signals` and
every taxonomy-F `pattern_id` at `minor`, so they can reach at most `SOFT_FLAGS` —
never an authorship or misconduct verdict. That cap is enforced in code
(`SURFACE_ONLY_SKILLS` in `tools/adjudicate_findings.py`), not just promised.

And an **eval harness** (`eval/`) proves the deterministic core on clean +
synthetically-corrupted fixtures every change — measured false-positive / recall,
not vibes.

## 🏗️ Architecture

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
        presentation-signals       surface/AI-flavor · auxiliary, capped at minor
        adversarial-case-builder   evidence-bound memo, no verdict · ARIS kill-argument
   │
   ▼  [adjudicate_findings.py]  rules, not a model → REPORT.md + report.json            ← deterministic
```

| Path | What |
|------|------|
| `skills/` | the seven auditor skills (LLM proposes findings, span-anchored) |
| `workflows/anti-autoresearch/` | the end-to-end orchestrator |
| `tools/` | deterministic spine: manifest/observability derivation · ledger builder · numeric checks · adjudicator |
| `schemas/` | JSON contracts: claims · finding · report · artifact manifest |
| `references/` | hack-pattern taxonomy (the core contribution) · observability levels · reviewer independence · forensics contract |
| `eval/` | clean + synthetic-corruption fixtures + the regression harness |
| `tests/` | gate unit tests for the adjudicator (the anti-slop invariants) |
| `docs/` | positioning vs existing work · limitations |

## ⚠️ Honest limitations

- **Forensics ≠ proof of misconduct.** Output is *flags for a human*, never an accusation.
- **PDF-only (L0) catches inconsistency + tells, not all fabrication** — it cannot
  verify external ground truth or run code.
- **False positives exist** (legitimate round numbers, single-seed pilots,
  deliberate scope choices). Hence tiers, FP-risk tags, and the eval harness — not
  a binary "guilty".
- **The taxonomy is a living document.** Adversaries who know a signal can route
  around it; this is a safety net, not a guarantee. See [docs/limitations.md](docs/limitations.md).

## 🧬 Provenance: derived from ARIS

[**ARIS — Auto Research in Sleep**](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)
is an AI research-agent skill platform that runs end-to-end research pipelines
(literature → idea → experiment → paper) — and does so **with integrity guardrails
built in**, which is what makes it a credible base for the auditor:

- 🛡️ **A three-layer audit stack** keeps ARIS's *own* output honest:
  `experiment-audit` (fake GT / score-normalization / phantom results),
  `result-to-claim` (is the claim scientifically supported?), and zero-context
  `paper-claim-audit` + `citation-audit` (do the reported numbers and references
  hold up?). Anti-Autoresearch is these same audits **pointed outward**.
- 🔬 **Cross-model adversarial review** is the core doctrine: the executor and the
  reviewer must be different model families, so no LLM ever judges its own output.
  Anti-Autoresearch inherits this *and* hardens it — here the model only **proposes**
  findings; a deterministic adjudicator decides.

**Two sides of one coin.** ARIS is how to do autoresearch *responsibly*;
Anti-Autoresearch is how to flag autoresearch that wasn't. A generator that publishes
its own audit stack knows precisely how these pipelines fail — because it engineered
against those failures from the inside. That is the perspective this repo brings.

👉 **ARIS main repo**: https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep

**How the skills map** — Anti-Autoresearch's skills are ARIS's audit skills, copied
and reframed for a **third party auditing an unknown submission** rather than an
author checking their own work: `consistency-audit` ← `paper-claim-audit`,
`experiment-forensics` ← `experiment-audit`, `citation-forensics` ← `citation-audit`,
`baseline-comparison-audit` ← `paper-claim-audit`, `adversarial-case-builder` ←
`kill-argument`, plus the new `evidence-ledger` spine and `presentation-signals`.

## 📖 Citation

Anti-Autoresearch is **derived from ARIS** and reuses its audit DNA. If this
repository helped your research / paper / review, please cite the ARIS methodology
paper:

```bibtex
@article{yang2026aris,
  title={ARIS: Autonomous Research via Adversarial Multi-Agent Collaboration},
  author={Yang, Ruofeng and Li, Yongcan and Li, Shuai},
  journal={arXiv preprint arXiv:2605.03042},
  year={2026}
}
```

## ⚖️ License

MIT — see [LICENSE](LICENSE).
