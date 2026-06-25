# Anti-Autoresearch

**Substantive integrity-forensics for research papers — especially machine-generated
(autoresearch / AI-Scientist-style) output.**

> 🛡️ **The dual of [ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)** — the ~12.5k★ autoresearch agent platform. ARIS is built to do autoresearch *responsibly*: it ships a multi-layer audit stack (experiment-integrity · result-to-claim · zero-context paper-claim audit · citation audit) so its **own** output stays honest. **Anti-Autoresearch is the other side of that coin** — the reviewer-side tool that catches autoresearch produced *without* those guardrails. Same audit DNA, pointed outward. ([What is ARIS?](#-what-is-aris--a-quick-pitch) · 中文 [README_CN.md](README_CN.md))

> Regardless of *who or what* wrote a paper, does the science hold together and
> reflect its own evidence? Anti-Autoresearch audits a submission for
> **self-consistency** and **fabrication**, and produces a span-anchored,
> reviewer-ready report. It is **not** an AI-text detector, and it does **not**
> judge misconduct — it surfaces discrepancies a human reviewer should investigate.

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

**This is not hypothetical.** Paraphrased from a public reviewer account during the
NeurIPS 2026 cycle (illustrative, not a citation), one batch maps almost
one-to-one onto the taxonomy this repo encodes:

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

The fourth case is this repo's thesis in one line: **surface polish is not
integrity.** (The reviewers' own summary: "LLM and multimodal are the disaster
zone; theory too — conclusions look solid, then the appendix is just GPT.")

## What it is — and is not

| | |
|---|---|
| ✅ **is** | self-consistency + fabrication forensics; evidence-ledger-anchored; observability-aware; reviewer/AC decision support; **+ auxiliary surface/AI-flavor signals (capped, never a verdict)** |
| ❌ **is not** | an AI-text classifier (Pangram / GPTZero / Binoculars), an AI-review detector, a misconduct verdict, or a co-author that edits the paper |

> On the surface signals (AI-flavor prose, duplicate tables, LLM-generated figures,
> page-padding): we **do** report them — reviewers ask for them — but as *weak,
> high-false-positive context* that the adjudicator caps at `minor` (so they can
> only ever say "look closer", never "this is broken" or "this is AI-written").
> That cap is enforced in code (`SURFACE_ONLY_SKILLS`), not just promised.

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
  adjudicator. The `eval/` harness gates these: **100% recall on the three
  deterministic patterns** (`HP-DELTA-ERROR`, `HP-NUM-INFLATE`, `HP-DUP-TABLE`)
  across the bundled fixtures, **zero clean false-positives**, every above-info
  finding ledger-anchored. This is the load-bearing, reproducible part — no model
  in the loop.
- **Agent-layer audits — alpha, require Claude + a cross-model reviewer.** The
  *semantic* skills (method-drift, ablation attribution, wrong-context citation,
  baseline adequacy, experiment-code integrity, and the auxiliary surface/AI-flavor
  signals) are `SKILL.md` contracts run by an agent via `/anti-autoresearch`. They
  propose span-anchored findings that the *same* deterministic adjudicator scores;
  they are not yet covered by the deterministic eval (semantic judgments can't be
  unit-tested the same way).

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
#   dup_table        SOFT_FLAGS             PASS   caught=HP-DUP-TABLE
#   headline_inflate SOFT_FLAGS             PASS   caught=HP-NUM-INFLATE
#   injected-defect recall: 100% (3 deterministic patterns) · clean FP: none

# 1b) gate unit tests (the anti-slop guarantee)
python3 tests/test_adjudicator.py

# 2) Build an evidence ledger from a real paper's LaTeX
python3 tools/build_claim_ledger.py --paper-id mypaper \
    --latex main.tex sections/*.tex --observability-level 1 --out claims.json

# 3) Run the deterministic consistency checks
python3 tools/check_numeric_consistency.py --ledger claims.json --out findings.json

# 4) Adjudicate into a report (deterministic verdict).
#    --ledger is REQUIRED: every above-info finding must quote a verbatim ledger
#    span, else it fails closed to info (the anti-slop guarantee).
python3 tools/adjudicate_findings.py --findings findings.json --ledger claims.json \
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

## 🌟 What is ARIS — A Quick Pitch

[**ARIS — Auto Research in Sleep**](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)
is a widely-used AI research-agent skill platform (2025–2026). It runs end-to-end
research pipelines (literature → idea → experiment → paper) — and it does so **with
integrity guardrails built in**, which is what makes it a credible base for the
auditor:

- ⭐ **~12.5k GitHub stars**, HuggingFace Daily Papers #1, 78+ research skills across 7+ platforms.
- 🛡️ **A three-layer audit stack** so ARIS's *own* output stays honest:
  `experiment-audit` (fake GT / score-normalization / phantom results),
  `result-to-claim` (is the claim scientifically supported?), and zero-context
  `paper-claim-audit` + `citation-audit` (do the reported numbers and references
  hold up?). Anti-Autoresearch is these same audits **pointed outward**.
- 🔬 **Cross-model adversarial review** is the core doctrine: the executor and the
  reviewer must be different model families (Claude × GPT-5.5 xhigh × Gemini), so no
  LLM ever judges its own output. Anti-Autoresearch inherits this *and* hardens it —
  here the model only **proposes** findings; a deterministic adjudicator decides.

**Two sides of one coin.** ARIS is how to do autoresearch *responsibly*;
Anti-Autoresearch is how to flag autoresearch that wasn't. A generator that
publishes its own audit stack knows precisely how these pipelines fail — because it
engineered against those failures from the inside. That is the perspective this repo
brings.

👉 **ARIS main repo**: https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep

### How the skills map

Anti-Autoresearch's skills are ARIS's audit skills, copied and reframed for a
**third party auditing an unknown submission** rather than an author checking their
own work: `consistency-audit` ← `paper-claim-audit`, `experiment-forensics` ←
`experiment-audit`, `citation-forensics` ← `citation-audit`,
`baseline-comparison-audit` ← `paper-claim-audit`, `adversarial-case-builder` ←
`kill-argument`, plus the new `evidence-ledger` spine and `presentation-signals`.

## Citation

Anti-Autoresearch is **derived from ARIS** and reuses its audit DNA. If you use this
repository in academic work, **please cite ARIS** (the parent project):

```bibtex
@article{aris2026,
  title={Auto-claude-code-research-in-sleep (ARIS): Autonomous ML Research via Cross-Model Collaboration},
  author={Yin, Wanshu and others},
  year={2026},
  howpublished={\url{https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep}},
  note={Technical Report arXiv:2605.03042}
}
```

To cite this repository specifically:

```bibtex
@misc{antiautoresearch2026,
  title={Anti-Autoresearch: Substantive Integrity Forensics for Autoresearch Papers},
  author={Yin, Wanshu and others},
  year={2026},
  howpublished={\url{https://github.com/wanshuiyin/Anti-Autoresearch}},
  note={A sibling project of ARIS (arXiv:2605.03042)}
}
```

## License

MIT — see [LICENSE](LICENSE).
