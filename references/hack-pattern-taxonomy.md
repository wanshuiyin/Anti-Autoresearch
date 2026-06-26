# Autoresearch Hack-Pattern Taxonomy

```
taxonomy_version: 0.3
last_reviewed: 2026-06-26
patterns: 39 hard (families A–G) + 2 advisory (no verdict weight)
status: living document — versioned; the version is stamped into every report
```

A catalog of the **specific** ways machine-driven research pipelines (and rushed
human work) produce papers that are internally inconsistent or unsupported by
their own evidence. This is the reusable IP of Anti-Autoresearch: it is curated by
the maintainers of an autoresearch system (ARIS), i.e. by people who have watched
these failures occur **from the generator's side**.

## How to read / use this file

The taxonomy is a **post-hoc mapping layer**, not a detector (see
`integrity-forensics-contract.md`). Auditors detect from the evidence ledger +
checklists; a finding *then* maps onto a pattern via `pattern_id`. Each pattern
carries its known **false-positive cases** so a mapped finding inherits the right
skepticism.

Every pattern declares:

- **`level`** — minimum observability level to *decide* it (L0 PDF-only … L2 repo+results).
- **`signals`** — what an auditor looks for.
- **`fp_cases`** — legitimate situations that look like the pattern (suppress / lower severity).
- **`severity_rule`** — when it is critical vs major vs minor.
- **`min_evidence`** — what must be cited before flagging above `info`.
- **`example`** — a minimal illustration.

Severity is always subject to the observability downgrade in
`observability-levels.md`: a pattern with `level: L2` flagged during an L0 run is
demoted to `info`.

---

## A. Numeric self-consistency (mostly L0)

### HP-NUM-INFLATE — headline number exceeds its own table
- **level:** L0
- **signals:** a value in abstract/intro/conclusion is more favorable than the
  same metric+setting in the results table/appendix.
- **fp_cases:** different setting genuinely (e.g. abstract quotes best config,
  table lists all configs — legitimate if the config is named); standard rounding.
- **severity_rule:** critical if the headline claim depends on the inflated value;
  major otherwise.
- **min_evidence:** both spans (abstract claim + table cell) with locations.
- **example:** abstract "achieves 85.3%"; Table 2 best row is 84.7% with no
  "best of" qualifier.

### HP-DELTA-ERROR — relative-improvement arithmetic is wrong
- **level:** L0
- **signals:** "improves by X%" where X ≠ computed (new−old)/old (or /old vs /new
  ambiguity used to inflate).
- **fp_cases:** absolute vs relative points stated explicitly; rounding.
- **severity_rule:** major; critical if the corrected delta flips a "large/
  significant" framing.
- **min_evidence:** the two operand claims + the stated delta span.
- **example:** "16% improvement" from 73.1→78.0 (actual +6.7% rel / +4.9 pts).

### HP-AGG-DRIFT — aggregation mismatch (best reported as mean)
- **level:** L0 (text), confirmable at L2
- **signals:** text says "average over N seeds" but the number matches the best
  seed, or N in text ≠ N in table.
- **fp_cases:** paper explicitly reports best AND mean; pilot honestly labeled.
- **severity_rule:** major; critical if variance is hidden and the gap is within
  plausible seed spread.
- **min_evidence:** the aggregation claim span + the table/seed span.

### HP-DENOM-DRIFT — denominator / population drift
- **level:** L0
- **signals:** two tables average over different subsets (e.g. "all tasks" vs
  "tasks where method applies") but body text treats them as the same number.
- **fp_cases:** subsets clearly delimited and not conflated.
- **severity_rule:** major.
- **min_evidence:** both table captions/headers + the conflating sentence.

### HP-UNIT-DIR-MISMATCH — unit or metric-direction confusion
- **level:** L0
- **signals:** % vs absolute points mixed; lower-better metric described as
  "higher is better" (or an improvement reported in the wrong direction).
- **fp_cases:** unconventional but internally consistent unit, clearly defined.
- **severity_rule:** minor→major depending on whether it flips a comparison.
- **min_evidence:** the metric definition span + the misusing span.

### HP-CAPTION-MISMATCH — caption ≠ content
- **level:** L0 (text) / L1 (source)
- **signals:** figure/table caption describes a method, axis, or N that the
  content does not show.
- **fp_cases:** caption summarizes a multi-panel figure loosely.
- **severity_rule:** minor unless the caption is the only place a key result is stated.
- **min_evidence:** caption span + content span.

### HP-APPENDIX-CONTRA — appendix contradicts main
- **level:** L0
- **signals:** an appendix table/number disagrees with the main-text version of
  the same quantity.
- **fp_cases:** appendix reports a superset/extended run clearly labeled as such.
- **severity_rule:** major; critical if the main-text (more favorable) value is
  the headline.
- **min_evidence:** both spans.

---

## B. Method & scope (L0)

### HP-METHOD-DRIFT — described method ≠ evaluated method
- **level:** L0 (suspicion) / L2 (confirm)
- **signals:** body describes method A, but experiments quietly run A-lite, A+oracle,
  A with extra training data, or a different backbone than claimed.
- **fp_cases:** ablation deliberately varying the method, clearly labeled.
- **severity_rule:** critical — this directly breaks the central claim.
- **min_evidence:** the method-description span + the experimental-setup span that
  diverges.
- **example:** method section claims "no test-time labels"; eval setup loads gold
  labels for calibration.

### HP-ABLATION-ATTRIB — attribution not isolated by the ablation
- **level:** L0
- **signals:** gain is attributed to component X, but no ablation isolates X (X is
  always bundled with Y).
- **fp_cases:** isolating ablation exists elsewhere; component is theoretically
  inseparable and the paper says so.
- **severity_rule:** major.
- **min_evidence:** the attribution claim + the ablation table.

### HP-SCOPE-INFLATE — scope language exceeds evidence
- **level:** L0
- **signals:** "comprehensive / extensive / robust / general / SOTA across the
  board" on a thin actual scope (few datasets, N=1–2, one domain).
- **fp_cases:** scope is genuinely broad; qualifiers are present.
- **severity_rule:** minor→major; pairs with HP-SCOPE counterpart in baseline if
  "SOTA" is claimed.
- **min_evidence:** the scope-language span + the actual-scope span (table of
  datasets/seeds).

### HP-THEOREM-SCOPE-DRIFT — abstract general, theorem narrow
- **level:** L0
- **signals:** abstract/title advertise generality; the formal result holds only
  under strong/unstated assumptions.
- **fp_cases:** assumptions stated up front and acknowledged in abstract.
- **severity_rule:** major (theory papers) — route headline check to
  adversarial-case-builder.
- **min_evidence:** the abstract claim span + the theorem statement span (with
  assumptions).

### HP-ARGUMENT-CHAIN-BREAK — the motivation → method → experiment chain doesn't connect
- **level:** L0
- **signals:** the problem the intro motivates, the mechanism the method proposes, and
  what the experiments actually measure don't line up; sections read disjointed
  ("前言不搭后语"); a section restates its claim in circular wording ("not even wrong"
  filler) instead of advancing it.
- **fp_cases:** a dense-but-valid argument the reader must work through; a modular paper
  with explicit cross-references.
- **severity_rule:** major; critical if the headline contribution rests on the broken link.
- **min_evidence:** the motivation span + the method/experiment span it fails to connect to.

### HP-CAUSAL-EVIDENCE-LEAP — a relation is concluded that no experiment tests
- **level:** L0 (claim visible) / L2 (confirm no supporting run)
- **signals:** "A and B correlate, therefore equivalent / causal"; the paper studies C
  but concludes "D affects C" with no experiment that varies D; equivalence or causation
  asserted from a correlation or a single setting.
- **fp_cases:** the relation is established *theoretically* (then it's a proof obligation —
  see family G); the supporting experiment exists elsewhere in the paper.
- **severity_rule:** major; critical if it is the central claim.
- **min_evidence:** the conclusion span + the (absent) experimental-design span for that relation.

---

## C. Baseline integrity (L0 stated / L2 verified)

### HP-MISSING-BASELINE — required comparison absent
- **level:** L0
- **signals:** the obvious/recent SOTA baseline for this task is not compared, yet
  "SOTA / best" is claimed.
- **fp_cases:** baseline is concurrent/unavailable; paper justifies omission.
- **severity_rule:** major; critical if the headline is a SOTA claim.
- **min_evidence:** the SOTA claim span + the baselines-present list (and the
  named missing baseline). Uses a domain baseline profile.

### HP-WEAK-BASELINE — baseline undertuned / config mismatch
- **level:** L0 (asymmetry visible) / L2 (configs)
- **signals:** proposed method gets more compute/tuning/data than the baseline;
  baseline run at unfavorable settings; non-matching configs in compared rows.
- **fp_cases:** identical budget documented; standard reference numbers cited.
- **severity_rule:** major.
- **min_evidence:** the two config/setup spans being compared.

### HP-SIG-OVERLAP — "outperforms" without separation
- **level:** L0
- **signals:** improvement claimed where reported error bars overlap, or no
  variance/seed count is reported at all for a small gap.
- **fp_cases:** large gap; significance test reported; deterministic metric.
- **severity_rule:** minor→major depending on gap vs (missing) variance.
- **min_evidence:** the comparison claim + the variance/seed evidence (or its absence).

---

## D. Experiment integrity (L2 — requires repo/results)

> These inherit directly from ARIS `shared-references/experiment-integrity.md`
> (#57/#131). At L0 they can only be raised as `info` "could-not-verify" signals.

### HP-FAKE-GT — ground truth derived from model outputs
- **level:** L2
- **signals:** eval "reference/target" is generated/derived from a model rather
  than dataset-provided, and reported as performance (not labeled `synthetic_proxy`).
- **fp_cases:** explicitly labeled proxy evaluation; self-supervised by design.
- **severity_rule:** critical.
- **min_evidence:** the eval-script line loading/deriving GT + the claim it supports.

### HP-SELF-NORM — score normalized by the model's own statistics
- **level:** L2
- **signals:** a metric divided by max/min/mean of the model's *own* outputs to
  approach 1.0; raw scores not shown.
- **fp_cases:** standard min–max across ALL methods incl. baselines; raw+normalized
  both shown.
- **severity_rule:** critical.
- **min_evidence:** the normalization expression + the reported headline score.

### HP-PHANTOM-RESULT — number with no backing artifact
- **level:** L2
- **signals:** a reported number references a result file/metric key that does not
  exist, or a function never called.
- **fp_cases:** result file renamed/moved but present; number from an external
  reference cited.
- **severity_rule:** critical.
- **min_evidence:** the claim span + the absent file/key path checked.

### HP-DEAD-METRIC — defined but never computed
- **level:** L2
- **signals:** a metric function exists in eval code but is never called / its
  output never appears in any result file, yet is discussed.
- **fp_cases:** utility kept for future use and not discussed as a result.
- **severity_rule:** major.
- **min_evidence:** the definition site + the (absent) call site.

### HP-SUSPICIOUS-REGULARITY — results "don't look like real runs"
- **signals:** numbers across configs/backbones related by a too-clean arithmetic
  pattern (constant additive/multiplicative offset between rows, implausibly smooth
  monotonicity, identical decimals across unrelated settings) — i.e. they look
  synthesized rather than measured. (Reported by real reviewers as "明显的加减乘除
  规律性,不像跑出来的".)
- **fp_cases:** genuinely deterministic metrics; small integer-valued scores;
  rounding coincidence; a real linear trend. **High FP — "looks fake" is a hunch.**
- **severity_rule:** **at L0/L1 this is `minor`, `false_positive_risk: high`, a
  *prompt to check* only — never a "this is fabricated" grade.** It rises to `major`
  **only at L2**, confirmed against the actual result files / code (emit with
  `observability_level_required: 2`, so a PDF-only run auto-demotes it). This split
  is mandatory: you cannot grade results as synthesized from a table alone.
- **min_evidence:** the table spans exhibiting the pattern + the arithmetic relation
  (L0); the result-file/code confirmation (L2).

### HP-PLACEHOLDER-DATA — AI placeholder / fake data left in the released code
- **level:** L2
- **signals:** released code still contains generated placeholder/fake data or the
  assistant's own annotations ("# fake data for plotting", "dummy", "TODO: replace with
  real data"), and a reported figure/number is produced from it.
- **fp_cases:** a clearly-labeled synthetic toy example or unit-test fixture that feeds
  no reported result.
- **severity_rule:** critical (a reported result is drawn from placeholder data).
- **min_evidence:** the code line with the placeholder + the paper number/figure it feeds.

### HP-RESULT-ARTIFACT-MISMATCH — code output ≠ the paper's numbers
- **level:** L2
- **signals:** running (or reading) the released code yields results different from the
  paper's reported numbers; the implementation diverges from the described method/equations.
- **fp_cases:** seed/version/hardware variance within a stated tolerance; a documented
  post-hoc correction.
- **severity_rule:** critical.
- **min_evidence:** the paper number + the code-produced value (or the implementation
  span that diverges from the method).

### HP-MISSING-REPRO-ARTIFACT — the artifacts the method needs to be checkable are absent
- **level:** L0 (stated) / L2 (verified)
- **signals:** an empirical / agent / LLM paper ships neither code nor the prompts/configs
  its results depend on; "code will be released" with nothing runnable; key
  hyperparameters or prompts omitted.
- **fp_cases:** a genuinely theoretical paper; anonymized-submission norms (route to a
  camera-ready expectation, lower severity).
- **severity_rule:** major (an empirical claim cannot be reproduced even in principle).
- **min_evidence:** the result claim + the (absent) artifact it would need.

---

## E. Citation integrity (L0)

### HP-CITE-HALLUC — fabricated reference
- **level:** L0
- **signals:** cited paper does not exist at the claimed arXiv id/DOI/venue;
  fabricated authors/year/venue; version mismatch.
- **fp_cases:** real paper with a typo'd id (FIX, not fabrication); preprint→venue
  migration.
- **severity_rule:** critical (fabricated) / major (wrong metadata).
- **min_evidence:** the bib entry + the canonical-source check result.

### HP-CITE-CONTEXT — real paper, wrong context
- **level:** L0
- **signals:** a real citation used to support a claim the cited paper does not
  make (or argues against).
- **fp_cases:** legitimate "see also / contrast with" framing; the claim is the
  citing paper's own.
- **severity_rule:** major.
- **min_evidence:** the citing sentence span + what the cited paper actually
  establishes.
- **example:** citing a self-refinement paper to support "self-feedback yields
  correlated errors" when it argues the opposite.

---

## F. Presentation & surface signals (auxiliary — NEVER a standalone verdict)

> ⚠️ **Read this preamble before using any F-pattern.** These are the "AI-flavor /
> low-effort" signals that reviewers notice first (generic prose, few/duplicated
> floats, LLM-looking figures, padding to fill the page limit, jargon-stuffing).
> They are **weak, high-false-positive, and presentation-level** — a polished paper
> can be fraudulent and a rough paper can be honest. So in this repo F-patterns:
> (a) are emitted only by `skills/presentation-signals`, (b) carry
> `false_positive_risk: high` by default, (c) are **capped at `minor` by the
> adjudicator** (`SURFACE_ONLY_SKILLS`) so they can contribute at most `SOFT_FLAGS`
> — they can never produce `HARD_FLAGS` on their own, and they are **not** an
> AI-generation verdict. Their job is to say *"combine with the substantive findings
> and look closer"*, nothing more. We are not an AI-text classifier; for that, use a
> dedicated detector.

### HP-DUP-TABLE — duplicate / near-identical tables
- **level:** L0 (deterministic via the ledger's table cells)
- **signals:** two tables share an identical (ordered) sequence of numeric cells —
  often padding, or a copy-paste that was never updated. (Reviewer: "两张表占满一页
  并且内容一模一样".)
- **fp_cases:** a deliberately repeated reference table; tiny tables that collide by
  chance.
- **severity_rule:** minor (capped). Pair with HP-PAGE-PADDING if used as filler.
- **min_evidence:** both table spans / the matching cell sequences.

### HP-THIN-FLOAT — too few figures/tables for the claimed scope
- **level:** L0
- **signals:** a full-length paper with almost no figures/tables while claiming
  broad empirical results. (Reviewer: "全文只有两个表一张图".)
- **fp_cases:** legitimately theoretical / short-format papers.
- **severity_rule:** minor (capped); high FP.
- **min_evidence:** the float count + the scope claim.

### HP-LLM-FIGURE — a figure appears machine-generated / decorative
- **level:** L0 (visual; needs the rendered PDF)
- **signals:** a "figure" that is an LLM-generated illustration rather than a real
  plot/diagram of results. (Reviewer: "图还是大模型生成的".)
- **fp_cases:** legitimate conceptual/teaser figures; well-made diagrams.
- **severity_rule:** minor (capped); high FP.
- **min_evidence:** the figure reference + caption span.

### HP-PAGE-PADDING — filler to reach the page limit
- **level:** L0
- **signals:** oversized floats, repeated content, or vacuous text used to fill
  required length; or conversely failing to fill it. (Reviewer: "就这还没写满9页".)
- **fp_cases:** legitimately concise work; venue-specific length norms.
- **severity_rule:** minor (capped); high FP.
- **min_evidence:** the padding span(s).

### HP-JARGON-STUFF — term-stuffing without substance
- **level:** L0
- **signals:** dense piling-up of technical terms where the surrounding argument
  carries no actual content. (Reviewer: "堆砌名词吗".)
- **fp_cases:** genuinely dense but correct technical writing.
- **severity_rule:** minor (capped); very high FP.
- **min_evidence:** the offending span.

### HP-AI-FLAVOR — generic LLM-flavored prose
- **level:** L0
- **signals:** hallmarks of unedited LLM text (boilerplate transitions, hedged
  filler, uniform paragraph shapes). **Gross cases only.**
- **fp_cases:** huge — many honest authors use LLM assistance; non-native writing;
  house style. This is the single most FP-prone pattern in the taxonomy.
- **severity_rule:** minor (capped); very high FP. **Never** treat as evidence of
  fabrication or as an authorship verdict.
- **min_evidence:** representative span(s) — illustrative, not probative.

### HP-DEFENSIVE-HEDGE — defensive "not X but Y" hedging instead of stating what was done
- **level:** L0
- **signals:** pervasive "this paper is not X, but rather Y" / "we do not claim …;
  instead …" framing — a tell of iteratively patching a draft with AI edit-suggestions —
  where the text defends against objections rather than directly stating what was built
  and shown. (Reviewer: "本文不是什么什么，而是什么什么…论文应该直接表达做了什么".)
- **fp_cases:** a single deliberate scoping sentence; a genuine related-work contrast.
- **severity_rule:** minor (capped, surface-only); high FP.
- **min_evidence:** representative hedge spans (≥2).

### HP-NARRATIVE-ARC-BREAK — abstract / intro lacks the expected substantive arc
- **level:** L0
- **signals:** the abstract reads like an experiment-log dump, or is vague "general"
  language with no specifics; so many undefined new terms it can't be understood; no
  background → contribution → evidence arc; an Introduction that doesn't go problem →
  why-hard → approach → validation. (Reviewer: "摘要写的像实验分析 / 读不到引言".)
- **fp_cases:** a legitimately terse abstract; non-native phrasing; field conventions.
- **severity_rule:** minor (capped, surface-only); high FP.
- **min_evidence:** the abstract/intro span + which arc element is missing.

## G. Proof & derivation integrity (L0/L1 from the written proof · CAN be critical)

> Adapted from ARIS `proof-checker` + `formula-derivation`, reframed to audit a third
> party's proofs. Broken math is the most-cited "obviously machine-written" tell in real
> reviews. Unlike family F these are **substantive** and **can be critical**: a theorem
> whose proof is circular or skips a load-bearing step does not support its claim. Owned
> by `skills/proof-derivation-forensics`. Decide from the *written* proof/derivation
> (L0/L1) — never assert "fabricated"; assert that the step shown does not hold. High FP
> care: a terse-but-valid step is not a gap; cite the exact line that fails.

### HP-PROOF-OBLIGATION-GAP — a required lemma / case / transition is missing
- **level:** L0 (claim) / L1 (full proof source)
- **signals:** the proof omits a nontrivial obligation the theorem needs — a missing case,
  an un-proved lemma invoked as fact, a "clearly / it follows that" across a real gap
  ("过不去的步骤用文字糊弄"), an existence/concentration/generic-position claim never shown.
- **fp_cases:** the step is genuinely standard and cited; the obligation is discharged in
  an appendix.
- **severity_rule:** major; critical if the headline theorem depends on the gap.
- **min_evidence:** the theorem statement + the proof span where the obligation is skipped.

### HP-PROOF-CIRCULARITY — the proof assumes what it sets out to prove
- **level:** L0 / L1
- **signals:** the conclusion (or an equivalent restatement) is used as a premise; the
  "proof" restates the claim in different words and calls it done ("车轱辘话复述当证明").
- **fp_cases:** a legitimate "WLOG / by symmetry" reduction; proof by contradiction that
  *assumes the negation* (not circular).
- **severity_rule:** critical — a circular proof proves nothing.
- **min_evidence:** the premise span + the conclusion span it duplicates.

### HP-DERIVATION-INVALID — an algebra / probability / calculus step does not follow
- **level:** L0 (if the step is shown) / L1
- **signals:** an adjacent derivation step is mathematically wrong — an illegal
  manipulation, a sign/factor error, a misapplied expectation/inequality, a wrong limit.
- **fp_cases:** a typo that doesn't affect the result (note as minor); a valid step the
  reader can fill in.
- **severity_rule:** major; critical if a headline equation/result depends on it.
- **min_evidence:** the step span + why it does not follow.

### HP-SYMBOL-SEMANTIC-DRIFT — a symbol / operator / inequality changes meaning mid-paper
- **level:** L0 / L1
- **signals:** a symbol, index, quantifier, operator, or inequality direction is used
  inconsistently across definition → formula → proof (e.g. "关键公式符号用反" — a key
  formula's operator reversed); ≤ vs ≥, argmin vs argmax, one variable name with two meanings.
- **fp_cases:** an explicitly redefined symbol with notice; standard overloading the paper declares.
- **severity_rule:** major; critical if it inverts a result.
- **min_evidence:** the definition span + the divergent-use span.

### HP-ASSUMPTION-SMUGGLE — the proof relies on an unstated stronger assumption
- **level:** L0 / L1
- **signals:** a derivation silently uses independence, convexity, smoothness,
  boundedness, i.i.d., or a regularity condition the theorem never assumes; the result
  holds only under that hidden assumption.
- **fp_cases:** the assumption is standard for the setting and stated in the setup; it is
  implied by a cited result.
- **severity_rule:** major (the theorem as stated is broader than what's proved); pairs
  with HP-THEOREM-SCOPE-DRIFT.
- **min_evidence:** the proof step using the assumption + the (absent) assumption in the
  theorem statement.

## Advisory signals (NOT in the 39 · zero verdict weight · reviewer-judgment only)

> These recur in real reviews but are **not decidable from the paper alone**, so they are
> NOT hard patterns and carry **no adjudicator weight**. A skill may surface them as an
> informational memo (like `adversarial-case-builder`); the human decides. They are never
> a verdict.

- **ADV-TRIVIAL-COMBINATION** — "standard A + B + C where A, B, C are all well-known" /
  "缝合 (stapling)". Novelty is a reviewer judgment; the tool can lay out the prior-work
  overlap, it cannot rule "trivial".
- **ADV-DUPLICATE-PUBLICATION** — a submission looks like a repackaged/duplicate of prior
  work. Decidable only against a corpus: an exact title/abstract/DOI match is reportable;
  the *absence* of a match is **not** evidence of originality. Surfaced as candidate
  overlap, never a verdict.

## Contributing a pattern

A new pattern is admissible only if it has: a concrete `signal`, ≥1 honest
`fp_case`, a `min_evidence` rule, and an `example` from a fixture in `eval/` or a
public case. Bump `taxonomy_version`, set `last_reviewed`, and add an
`eval/expected_findings/` entry so the eval harness measures its false-positive
rate. Patterns that fire with high FP in eval are demoted, not shipped silently.
