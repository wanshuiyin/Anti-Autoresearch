# Autoresearch Hack-Pattern Taxonomy

```
taxonomy_version: 0.4
last_reviewed: 2026-06-28
patterns: 51 hard (families A–H) + 2 advisory (no verdict weight)
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

### HP-GRANULARITY-IMPOSSIBLE — a reported proportion is unachievable for its integer N (GRIM)
- **level:** L0 (deterministic via `tools/check_stat_consistency.py`)
- **signals:** an accuracy / success / error / proportion reported as a percentage to
  d decimals over N integer items does not equal round(100·k/N) at that precision for
  ANY integer k in [0,N] (the GRIM test). E.g. "84.7% on 500 items" is impossible —
  500·0.847 = 423.5, and k=423→84.6%, k=424→84.8%, so 84.7% rounds from no integer.
- **fp_cases:** N unknown/non-integer (cannot run); a macro/weighted/balanced average or
  a *relative* "improved by X%" figure rather than a simple k/N proportion (excluded);
  normalized non-count metrics (F1, AUC, BLEU, ROUGE, perplexity, mAP, IoU — excluded,
  not k/N); excluded/invalid trials shifting the effective N; large N where the
  granularity step (100/N pts) is finer than the display resolution (10⁻ᵈ) — **skip as
  vacuous**; a percentage that is a *mean over seeds/runs*, not a proportion over items.
- **severity_rule:** minor; major if the impossible value is a headline metric the claim
  rests on. Not critical from text alone — consistent with a transcription typo, not only
  with fabrication.
- **min_evidence:** the sentence span reporting the percentage + the integer N it is over.
- **ack:** the GRIM test (Brown & Heathers, 2017); ref impl `scrutiny` (Jung, MIT) — re-implemented from the method, no code reused.

### HP-VARIANCE-IMPOSSIBLE — a reported SD is too large for a bounded metric (GRIMMER / Bhatia–Davis)
- **level:** L0 (deterministic via `tools/check_stat_consistency.py`)
- **signals:** a standard deviation reported at mean μ for a metric bounded in [a,b]
  exceeds the largest SD such a variable can have: by Bhatia–Davis Var ≤ (b−μ)(μ−a), and
  by Popoviciu SD ≤ (b−a)/2 (with the sample Bessel factor √(n/(n−1)) when n is known).
  E.g. mean 98%, SD 18% over 5 seeds is impossible: the cap is ≈15.7%.
- **fp_cases:** the metric's range is not bounded (loss, perplexity, MSE, latency, reward
  — excluded); the dispersion is a **SEM / CI / error-bar** not an SD (requires an explicit
  SD label, else skipped); SD over seeds vs over items (match n to the population); the
  Bessel n vs n−1 convention; mean and SD on different scales; μ outside [a,b].
- **severity_rule:** major (a mathematically impossible reported uncertainty); critical if
  a headline error-bar/significance conclusion depends on it; minor if incidental.
- **min_evidence:** the span reporting mean ± SD + the metric's range; the sample size n when stated.
- **ack:** GRIMMER (Anaya, 2016) + the Bhatia–Davis / Popoviciu variance inequalities — re-derived, no code reused.

### HP-STAT-INCONSISTENCY — reported p contradicts its own test statistic (statcheck)
- **level:** L0 (deterministic via `tools/check_stat_consistency.py`; z = stdlib, t/F/χ²/r = optional scipy)
- **signals:** the p recomputed from a reported test statistic + df disagrees with the
  reported p, AND the reported p claims a .05 significance the statistic cannot support
  under any valid reading. z is exact (standard normal); t/F/χ²/r use an optional scipy
  backend. E.g. "z = 1.10, p = .036" — z=1.10 gives two-tailed p ≈ .27.
- **fp_cases:** one-tailed vs two-tailed (a reported p ≈ half the two-tailed p is
  **accepted, never flagged**); multiple-comparison / Bonferroni / FDR-adjusted p (a
  *larger* reported p — the core emits ONLY overstated-significance, so adjustments never
  false-positive); Welch / Greenhouse–Geisser fractional df (skipped); exact / permutation
  / bootstrap p; "p < .05" bounds; rounding of the statistic; missing scipy backend (skipped).
- **severity_rule:** major when the .05 decision flips toward overstated significance;
  critical if that result is the headline. (Understated / decision-unchanged discrepancies
  are not emitted by the deterministic core — too FP-prone.)
- **min_evidence:** the span reporting the statistic + df + p; the recomputed p interval and the backend are in the finding's provenance.
- **ack:** the recompute-from-statistic concept of **statcheck** (Nuijten & Epskamp) — GPL-3, credited by name only, no code reused; FP taxonomy informed by the statcheck critique (arXiv:2408.07948).

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

### HP-RESOURCE-IDENTITY-MISMATCH — a named dataset/benchmark/model contradicts its public record
- **level:** L0/L1 (the stated property is in the text), decided against the public registry
  (HuggingFace dataset/model cards, Papers-with-Code) — an external lookup, like HP-CITE-HALLUC,
  so `observability_level_required: 0`; a **repo-proven** wrong resource (released code loads a
  different dataset/model than the paper names) rises to **L2**.
- **signals:** a named resource is described with a checkable public-record property the
  registry contradicts — ImageNet-1k stated with the wrong #classes/image-count, a model's
  parameter count off from its card, a "SOTA 91.2 on <benchmark>" disagreeing with that
  benchmark's public leaderboard. The executor gathers the registry fact, the reviewer judges
  the discrepancy (gather-facts-then-judge, like citation-forensics). ROUTING: a claimed
  leaderboard-SOTA number vs the public leaderboard is the baseline form → family C
  (`baseline-comparison-audit`); a repo-proven wrong resource → family D, L2
  (`experiment-forensics`); the general card-identity form is decided here in B.
- **fp_cases:** a legitimate subset/variant (ImageNet-100, a 10% split, a distilled/quantized
  model) named as such; version differences (ImageNet-21k vs -1k, model v1 vs v2); the paper
  explicitly redefines the resource; a stale/ambiguous registry or a leaderboard updated after
  submission → `needs_external_check`, never a guessed "wrong".
- **severity_rule:** major; critical if the mis-described resource is load-bearing for the
  headline (the SOTA number that *is* the contribution); minor if peripheral. An
  under-specified (not contradicted) subset/version is at most minor / `needs_external_check`.
- **min_evidence:** the paper claim naming the resource + its stated property (the anchor) +
  the canonical registry record (HF card / Papers-with-Code URL + accessed date) in description.
- **ack:** generalizes the **Seek & Blastn** technique (Labbé et al. 2019 — flags papers whose
  stated sequence reagents contradict public sequence databases) to ML datasets/models vs HF
  cards / Papers-with-Code; our adaptation, not a port.

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
- **signals:** a *substantive* missing link in the argument — the problem the intro
  motivates, the mechanism the method proposes, and the quantity the experiments measure
  are logically disconnected: e.g. the method addresses a different problem than the one
  motivated, or the experiments measure something the method's claimed mechanism does not
  predict. This is about the *content* of the chain, not its prose. Mere stylistic
  disjointedness, "前言不搭后语" reading, or filler wording is the surface tell
  HP-NARRATIVE-ARC-BREAK (F-family, capped minor) — not this pattern.
- **fp_cases:** a dense-but-valid argument the reader must work through; a modular paper
  with explicit cross-references that does connect on inspection.
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

### HP-ACRONYM-DRIFT — the same component/term is named or expanded inconsistently
- **level:** L0 (decidable from the text; the conflicting spans are explicit)
- **framing note:** a checkable SELF-INCONSISTENCY in terminology — NOT a "looks AI-written"
  vibe signal. The finding asserts only that two spans name the same load-bearing object
  incompatibly; never authorship or misconduct. (Reviewer: "模块名冗长甚至有前后缩写不一致".)
- **signals:** one acronym is defined with two incompatible expansions; OR a single
  load-bearing component / method / module is referred to by two or more incompatible names
  or acronyms across the paper (abstract ↔ method ↔ experiments), so a reader cannot tell
  whether they are the same thing.
- **fp_cases:** a standard acronym legitimately reused for different things; an author-declared
  overloading; a local, clearly-scoped section abbreviation; near-synonyms the paper explicitly
  equates. Require the two spans to name the SAME load-bearing object AND be genuinely
  incompatible — else do not raise. (Verbose names / bold-spam alone are presentation only →
  HP-JARGON-STUFF, not this.)
- **severity_rule:** minor; major only if the drift makes a central method/result ambiguous.
- **min_evidence:** the two conflicting name/expansion spans for the same object.

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
- **level:** L0/L1 (the too-clean pattern is visible in the reported tables) / L2 (confirm against the real run/result files)
- **signals:** numbers across configs/backbones related by a too-clean arithmetic
  pattern (constant additive/multiplicative offset between rows, implausibly smooth
  monotonicity, identical decimals across unrelated settings) — i.e. they look
  synthesized rather than measured. (Reported by real reviewers as "明显的加减乘除
  规律性,不像跑出来的".) Two named formal screens articulate the same hunch (advisory,
  L2-confirmed): the **Carlisle method** (baseline summary statistics / p-values too uniform
  or too extreme to be a real random sample) and **Benford's-law** first-digit screening over
  a large pool (≥~100) of reported numbers.
- **fp_cases:** genuinely deterministic metrics; small integer-valued scores;
  rounding coincidence; a real linear trend. Benford is **invalid** on small pools (<~100) and
  bounded ranges (accuracies in [0,1], normalized/fixed-precision scores); Carlisle flags
  legitimately uniform p-values under a true null. **High FP — "looks fake" is a hunch.**
- **severity_rule:** **at L0/L1 this is `minor`, `false_positive_risk: high`, a
  *prompt to check* only — never a "this is fabricated" grade.** It rises to `major`
  **only at L2**, confirmed against the actual result files / code (emit with
  `observability_level_required: 2`, so a PDF-only run auto-demotes it). This split
  is mandatory: you cannot grade results as synthesized from a table alone.
- **ack:** the named screens credit the Carlisle method (Carlisle 2017) and Benford's-law
  first-digit screening (Diekmann 2007) — paraphrased, kept strictly advisory.
- **min_evidence:** the table spans exhibiting the pattern + the arithmetic relation
  (L0); the result-file/code confirmation (L2).

### HP-PLACEHOLDER-DATA — placeholder / fake data left in the released code
- **level:** L2
- **signals:** released code still contains placeholder/fake data or stub annotations
  ("# fake data for plotting", "dummy", "TODO: replace with real data"), and a reported
  figure/number is produced from it. (Flag the checkable code artifact; do not infer *who*
  wrote the annotation — the provenance is irrelevant to the discrepancy.)
- **fp_cases:** a clearly-labeled synthetic toy example or unit-test fixture that feeds
  no reported result.
- **severity_rule:** critical (a reported result is drawn from placeholder data).
- **min_evidence:** the code line with the placeholder + the paper number/figure it feeds.

### HP-RESULT-ARTIFACT-MISMATCH — code/artifact output ≠ the paper's numbers
- **level:** L2
- **signals:** running (or reading) the released code / result artifacts (logs, checkpoints,
  result JSON) yields numbers different from the paper's reported values for the *same*
  experiment cell. Strictly artifact-number vs paper-number. (An implementation that diverges
  from the *described method/equations* is HP-METHOD-DRIFT — route there, not here.)
- **fp_cases:** seed/version/hardware variance within a stated tolerance; a documented
  post-hoc correction.
- **severity_rule:** critical.
- **min_evidence:** the paper number + the code/artifact-produced value for the same cell.

### HP-MISSING-REPRO-ARTIFACT — the artifacts the method needs to be checkable are absent
- **level:** L2 — an absent-artifact flag is only verdict-bearing once the repo / artifact
  set is actually inspected. At L0/L1 the reviewer can scan the manuscript for an
  availability statement / repo URL ("code is available at", "data availability", github /
  zenodo / osf / huggingface links): an empirical paper with **none stated** is surfaced as
  `info` / `needs_external_check` — "no artifact is *stated*" is checkable from text, but
  "artifacts are *missing*" is not assertable from a PDF, so it stays L2-verdict-bearing.
- **signals:** an empirical / agent / LLM paper ships neither code nor the prompts/configs
  its results depend on; no data/code availability statement and no repo link in the text;
  "code will be released" with nothing runnable; key hyperparameters or prompts omitted.
- **fp_cases:** a genuinely theoretical paper; anonymized-submission norms (route to a
  camera-ready expectation, lower severity); an availability statement in a footnote /
  acknowledgements / non-standard phrasing the scan missed → `info`, never a hard L0 flag.
- **severity_rule:** major at L2 (an empirical claim cannot be reproduced even in principle);
  below L2 it is informational only — the L0/L1 scan only flags the *absence of a stated*
  artifact, never asserts one is missing.
- **min_evidence:** the result claim + the (absent) artifact it would need.
- **ack:** the availability-statement scan adapts the approach of **ODDPub** (Riedel et al.
  2020) and **RTransparent** (Serghiou et al. 2021) — both GPL/AGPL; prior art credited, their
  keyword sets to be reimplemented from the papers, no code vendored. *(L0/L1 scan planned; the
  L2 verdict path is the shipped behavior.)*

---

## E. Citation integrity (L0)

### HP-CITE-HALLUC — fabricated reference
- **level:** L0
- **framing note:** "identifier-hijacking" names the *effect* (an id resolving to a record whose
  title/authors don't match the citation); the finding asserts only that checkable metadata
  mismatch — never intent, and report wording stays neutral (no "deception").
- **signals:** cited paper does not exist at the claimed arXiv id/DOI/venue; fabricated
  authors/year/venue; version mismatch. Two sub-signals (fabricated-citation taxonomy, Ansari
  2026): **identifier-hijacking** — the DOI/arXiv id *resolves* but the resolved record's
  title/authors do NOT match the citation (a plain existence check passes it, so the title/author
  match against the resolved record is the load-bearing test); **placeholder citation** — a
  leftover stub never replaced ("[ref?]", "[CITATION]", "\cite{XXX}", "TODO: cite").
- **fp_cases:** real paper with a typo'd id (FIX, not fabrication); preprint→venue migration; an
  id that resolves to a newer *version of the same work* (not a hijack); a placeholder in a
  clearly-marked working draft.
- **severity_rule:** critical (no record resolves / id resolves to an unrelated work) / major
  (wrong metadata, or a load-bearing placeholder).
- **min_evidence:** the bib entry + the canonical-source check result — for identifier-hijacking,
  the resolved record's title/authors vs the cited ones.
- **ack:** the identifier-hijacking / placeholder sub-signals are from the fabricated-citation taxonomy of Ansari (2026), arXiv:2602.05930.

### HP-CITE-CONTEXT — real paper, wrong context
- **level:** L0
- **signals:** a real citation used to support a claim the cited paper does not make (or argues
  against). Includes the **semantic-hallucination** case — a real reference attached to a
  plausible-but-nonexistent finding / wrong-claim attribution (the paper exists; the attributed
  claim does not). Each citing sentence may carry an **auxiliary intent label** ∈
  {support | contrast | mention}; a *support*-labeled cite whose cited work doesn't support the
  claim is the dangerous case, a *contrast* / *mention* reading is the common FP. The label is
  auxiliary and **never a standalone verdict**.
- **fp_cases:** legitimate "see also / contrast with" framing (intent = contrast/mention); the
  claim is the citing paper's own contribution; a low-confidence label (advisory only).
- **severity_rule:** major; the intent label only flags candidates, never raises a verdict on its own.
- **min_evidence:** the citing sentence span + what the cited paper actually establishes (+ the
  auxiliary intent label, with confidence).
- **example:** citing a self-refinement paper to support "self-feedback yields correlated errors"
  when it argues the opposite (intent = support; cited work does not support → flag).
- **ack:** the support/contrast/mention label is inspired by scite Smart Citations (Nicholson et al. 2021 — proprietary, conceptual credit) + the Support/Refute/NEI schema of SciFact (Wadden et al. 2020).

### HP-CITE-RETRACTED — reliance on a retracted / withdrawn reference
- **level:** L0 (external retraction lookup — Crossref / Retraction-Watch open metadata; cite source + date)
- **framing note:** retraction status is a *checkable fact about the cited work* (a
  publisher/author action), not a judgment about the citing authors. The finding asserts only
  that a retracted work is relied on with no note of the retraction — never why it was retracted.
- **signals:** a cited reference resolves to a RETRACTED or withdrawn paper (journal/publisher
  retraction, or an arXiv withdrawal) and the citing sentence relies on it to support a claim
  with no acknowledgement of the retraction. Status is looked up from open retraction metadata
  (Crossref retraction relations / Retraction Watch), source + date recorded — never inferred.
- **fp_cases:** the paper cites the work *expressly to discuss* the retraction (cautionary /
  related-work — intent is not reliance); the retraction post-dates submission; an "expression of
  concern" / erratum / correction (not a full retraction — lower severity); an arXiv version
  withdrawn but a later cited version supersedes it.
- **severity_rule:** major if the retracted reference is load-bearing; info/minor if cited
  expressly to discuss the retraction, or the retraction post-dates submission.
- **min_evidence:** the citing sentence span + the retraction record (source + date + URL).
- **ack:** follows the "Feet of Clay" detector of the Problematic Paper Screener (Cabanac, Labbé,
  Magazinov); status from the Retraction Watch database via Crossref / Retraction-Watch open metadata.

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

### HP-PIPELINE-ARTIFACT — exact-match leftover pipeline/assistant/template string
- **level:** L0 (deterministic via `tools/check_presentation.py`, like HP-DUP-TABLE)
- **framing note:** the textual analog of HP-PLACEHOLDER-DATA — it flags the **checkable
  verbatim string** and asserts only that the string is present, never who/what wrote it.
  An exact case-insensitive substring match (NOT stylometry, NOT an AI-text classifier),
  which is why it is the one **low-FP** family-F pattern; still never an authorship verdict.
- **signals:** a string that should never appear in finished prose survives into the
  text/caption/cell — an assistant leftover ("as an AI language model", "regenerate
  response", "as of my last knowledge update") or an unfilled template placeholder
  ("<your text here>", "[INSERT X]", "TODO: cite", "lorem ipsum"). Curated list lives in
  `tools/check_presentation.py` (`PIPELINE_ARTIFACT_PHRASES`).
- **fp_cases:** a paper that legitimately quotes/studies such strings (a paper *about*
  LLM outputs/refusals, a tortured-phrase survey, a reproduced prompt template). The check
  is deterministic so it WILL fire — the documented fp_case is what the human uses to dismiss.
- **severity_rule:** minor (capped, surface-only) — at most SOFT_FLAGS. `false_positive_risk`
  is **low** (the match is exact), but the surface cap still holds. Never evidence of fabrication.
- **min_evidence:** the verbatim leftover span (a short window around the hit so it anchors).
- **routing:** if the leftover FEEDS a reported number/figure it is HP-PLACEHOLDER-DATA
  (family D, critical), not this surface pattern.
- **ack:** the "by-product / ChatGPT-fingerprint" detector of the Problematic Paper Screener
  (Cabanac, Labbé & Magazinov) — adapted to a ledger-anchored, deterministic check.

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
- **signals:** hallmarks of unedited LLM text — connective filler overused as a tic
  ("It is worth noting that", "值得注意的是", "意义在于", "not only … but also", chains of
  "however / therefore / moreover", clichéd em-dashes / semicolons, "therefore" dropped
  mid-sentence), flowery empty adverbs ("elegantly", "theoretically"), hedged filler, uniform
  paragraph shapes. **Gross cases only.** Distinct from HP-DEFENSIVE-HEDGE (the specific
  not-X-but-Y defensive posture). These remain illustrative — a high-FP surface note, never an
  authorship verdict; we are not a vibe/AI-text classifier.
- **fp_cases:** huge — many honest authors use LLM assistance; non-native writing;
  house style. This is the single most FP-prone pattern in the taxonomy.
- **severity_rule:** minor (capped); very high FP. **Never** treat as evidence of
  fabrication or as an authorship verdict.
- **min_evidence:** representative span(s) — illustrative, not probative.

### HP-DEFENSIVE-HEDGE — defensive "not X but Y" hedging instead of stating what was done
- **level:** L0 (a conservative deterministic density arm in `tools/check_presentation.py`,
  `DEFENSIVE_HEDGE_PATTERNS`; plus the agent-layer reading for sub-threshold cases)
- **signals:** a high *density* of defensive-contrast constructions that defend against an
  anticipated objection instead of directly stating what was built and shown. The curated
  strong templates the deterministic screen counts: "we do not claim …", "we make no claim",
  "this paper does not (claim/argue/prove) …", "this does not mean/imply …", "our goal is not
  X but (rather) Y", "not X but rather Y"; 中文 "本文并不主张 / 本文不是要证明 / 这并不意味着 /
  我们的目的不是…而是…". A sharper sub-signal: the text **volunteers a self-incriminating
  limitation** that flags an attack surface a reviewer would not otherwise raise (e.g. "We do
  not claim our cases are representative of all contexts" — which makes a reviewer think
  *representativeness is a problem here*). The checkable signal is the **recurrence of the
  hedge shape, NOT who wrote it** — never infer AI authorship or editing provenance. (Reviewer:
  "本文不是什么什么，而是什么什么…论文应该直接表达做了什么"; another likens defensive patches to
  "往有细小裂纹的瓷器上糊泥巴" —补上问题反而提醒别人这里有问题且破坏整体性.) Differs from
  HP-AI-FLAVOR: that is generic LLM-flavored prose; this is the specific not-X-but-Y posture.
- **deterministic screen:** fires only on a genuine PATTERN — ≥4 distinct stance-constrained
  strong-template `scope` sentences across ≥2 non-excluded sections (excluding Limitations /
  Related-Work / Ethics / Broader-Impact, where a hedge is expected) **and** ≥25% of all
  non-excluded scope sentences. One scoping sentence never trips it (precision >> recall). A bare
  "not X but rather Y" needs an author/paper-stance subject to count (so "not convex but rather
  piecewise smooth" is ignored). PDF-text ledgers label every claim section `unknown`, so this
  deterministic arm is effectively silent unless LaTeX section labels exist; the agent-layer
  reading covers those cases.
- **fp_cases:** a single deliberate scoping sentence; a genuine related-work contrast; a
  Limitations paragraph (expected to hedge). **Note the real tension:** some venues / AI
  reviewers penalize the *absence* of caveats, so measured hedging is a legitimate strategic
  choice, **not** misconduct — which is exactly why this stays capped at minor and never
  verdict-bearing.
- **severity_rule:** minor (capped, surface-only); high FP. **Never** an authorship /
  AI-generation verdict.
- **routing:** if a specific hedge instead reveals a *real* scope/evaluation limitation, route
  THAT to HP-SCOPE-INFLATE (family B) or eval-design-forensics (family H) — the substantive
  problem, not the rhetorical shape.
- **min_evidence:** representative hedge spans (≥2), span-anchored to the ledger.
- **ack:** a widely-shared 2026 community thread on "防御性写作" in AI-assisted paper revision
  (the not-X-but-Y posture, pre-emptive self-incrimination, and invented codenames — the last
  captured as HP-INVENTED-CODENAME).

### HP-NARRATIVE-ARC-BREAK — abstract / intro lacks the expected substantive arc
- **level:** L0
- **signals:** the abstract reads like an experiment-log dump, or is vague "general"
  language with no specifics; so many undefined new terms it can't be understood; no
  background → contribution → evidence arc; an Introduction that doesn't go problem →
  why-hard → approach → validation. (Reviewer: "摘要写的像实验分析 / 读不到引言".)
- **fp_cases:** a legitimately terse abstract; non-native phrasing; field conventions.
- **severity_rule:** minor (capped, surface-only); high FP.
- **min_evidence:** the abstract/intro span + which arc element is missing.

### HP-INVENTED-CODENAME — undefined internal project/run codename written into the paper
- **level:** L0 (semantic — **agent-layer only, no deterministic detector**: judging "internal-
  flavored undefined codename vs legitimate method name" is not regex-able without heavy FP)
- **signals:** an experiment/run/system **codename that reads like a generation-pipeline
  internal label** appears in a table, caption, section heading, or core-results sentence and is
  **never defined** — and it is not the paper's formal method name, a standard dataset/split, an
  ablation label, or a config id. (Community observation: "agent 喜欢自创一些代号写进论文里" — an
  agent referring to its own runs as, say, "Experiment Set Gamma" / "PHX-v3" that the paper never
  introduces.) The checkable signal is an **undefined identifier used as if defined**, not who
  wrote it — no stylometry, no authorship verdict.
- **fp_cases:** legitimate named methods/systems; established benchmark/split names; deliberate
  internal-but-defined release tags; ablation labels defined elsewhere. Very high FP — require the
  codename to be (a) undefined in the text AND (b) load-bearing (≥2 occurrences or in a results
  table), else do not raise.
- **severity_rule:** minor (capped, surface-only); high FP. Recommended action is only "ask the
  authors to define the term or de-internalize the naming." Never a misconduct/authorship verdict.
- **routing:** if the codename points to a **missing results file / unreproducible run**, that is
  HP-MISSING-REPRO-ARTIFACT or HP-PHANTOM-RESULT (family D, L2) — not this surface signal.
- **min_evidence:** the codename span(s) + the absence of any defining sentence.

## G. Proof & derivation integrity (verdict-bearing at L1 — needs the LaTeX source · CAN be critical)

> Adapted from ARIS `proof-checker` + `formula-derivation`, reframed to audit a third
> party's proofs. Broken math is the most-cited "obviously machine-written" tell in real
> reviews. Unlike family F these are **substantive** and **can be critical**: a theorem
> whose proof is circular or skips a load-bearing step does not support its claim. Owned
> by `skills/proof-derivation-forensics`. **Verdict-bearing only at L1** — decide from the
> LaTeX *source*, because PDF-extracted math is unreliable (mangled symbols, subscripts,
> equation structure); at an L0 (PDF-only) run a proof flaw is surfaced as a candidate
> (`info`) only. Never assert "fabricated"; assert that the step shown does not hold. High
> FP care: a terse-but-valid step is not a gap; cite the exact line that fails.

### HP-PROOF-OBLIGATION-GAP — a required lemma / case / transition is missing
- **level:** L1 (the LaTeX proof source; at L0 surface `info` only)
- **signals:** the proof omits a nontrivial obligation the theorem needs — a missing case,
  an un-proved lemma invoked as fact, a "clearly / it follows that" across a real gap
  ("过不去的步骤用文字糊弄"), an existence/concentration/generic-position claim never shown.
- **fp_cases:** the step is genuinely standard and cited; the obligation is discharged in
  an appendix.
- **severity_rule:** major; critical if the headline theorem depends on the gap.
- **min_evidence:** the theorem statement + the proof span where the obligation is skipped.

### HP-PROOF-CIRCULARITY — the proof assumes what it sets out to prove
- **level:** L1 (at L0 surface `info` only)
- **signals:** the conclusion (or an equivalent restatement) is used as a premise; the
  "proof" restates the claim in different words and calls it done ("车轱辘话复述当证明").
- **fp_cases:** a legitimate "WLOG / by symmetry" reduction; proof by contradiction that
  *assumes the negation* (not circular).
- **severity_rule:** critical — a circular proof proves nothing.
- **min_evidence:** the premise span + the conclusion span it duplicates.

### HP-DERIVATION-INVALID — an algebra / probability / calculus step does not follow
- **level:** L1 (at L0 surface `info` only — PDF math extraction is unreliable)
- **signals:** an adjacent derivation step is mathematically wrong — an illegal
  manipulation, a sign/factor error, a misapplied expectation/inequality, a wrong limit.
- **fp_cases:** a typo that doesn't affect the result (note as minor); a valid step the
  reader can fill in.
- **severity_rule:** major; critical if a headline equation/result depends on it.
- **min_evidence:** the step span + why it does not follow.

### HP-SYMBOL-SEMANTIC-DRIFT — a symbol / operator / inequality changes meaning mid-paper
- **level:** L1 (at L0 surface `info` only)
- **signals:** a symbol, index, quantifier, operator, or inequality direction is used
  inconsistently across definition → formula → proof (e.g. "关键公式符号用反" — a key
  formula's operator reversed); ≤ vs ≥, argmin vs argmax, one variable name with two meanings.
- **fp_cases:** an explicitly redefined symbol with notice; standard overloading the paper declares.
- **severity_rule:** major; critical if it inverts a result.
- **min_evidence:** the definition span + the divergent-use span.

### HP-ASSUMPTION-SMUGGLE — the proof relies on an unstated stronger assumption
- **level:** L1 (at L0 surface `info` only)
- **framing note:** the id is a mnemonic for the *effect* (an assumption present in the
  proof but absent from the statement); the finding asserts only that checkable
  discrepancy — never authorial intent or misconduct.
- **signals:** a derivation uses independence, convexity, smoothness, boundedness, i.i.d.,
  or a regularity condition the theorem statement never lists; the result holds only under
  that additional assumption.
- **fp_cases:** the assumption is standard for the setting and stated in the setup; it is
  implied by a cited result.
- **severity_rule:** major (the theorem as stated is broader than what's proved); pairs
  with HP-THEOREM-SCOPE-DRIFT.
- **min_evidence:** the proof step using the assumption + the (absent) assumption in the
  theorem statement.

### HP-UNDEFINED-NOTATION — a load-bearing symbol is used but never defined
- **level:** L1 (verdict-bearing on the LaTeX source; at L0 PDF surface `info` only — PDF math
  extraction is unreliable)
- **framing note:** a checkable rigor/readability gap — a symbol / operator / index carries
  meaning in a key equation, lemma, or proof yet is **never defined and is not inferable from
  standard convention**. The finding asserts only that absence-of-definition, never authorship.
  Distinct from HP-SYMBOL-SEMANTIC-DRIFT (a *defined* symbol that CHANGES meaning mid-paper);
  here the symbol is simply never pinned down. The "short clause then a wall of formulas" style
  on its own is presentation only (HP-NARRATIVE-ARC-BREAK / HP-PAGE-PADDING), not this.
- **signals:** a central equation / theorem / algorithm uses notation (a variable, operator,
  subscript/superscript, or set) with no defining sentence anywhere and no standard reading, so
  the result cannot be checked as written. (Reviewer: "method 部分全是没有 denote 的符号和公式".)
- **fp_cases:** notation genuinely standard in the subfield; a symbol defined in a
  figure/caption/appendix the reader can find; reused notation from a cited setup. Require the
  symbol to be load-bearing (it appears in a claimed result/proof) AND undefined.
- **severity_rule:** major if a checkable result/proof depends on the undefined symbol; minor if
  peripheral. PDF-only (L0): `info`.
- **min_evidence:** the equation/proof span using the symbol + the (absent) definition.

## H. Evaluation design & reporting validity (L0/L1 stated · confirmed at L2 · CAN be critical)

> Adapted from the ML-evaluation-methodology literature — the leakage taxonomy of
> Kapoor & Narayanan (2023), the LLM-as-judge validity work (MT-Bench self-enhancement,
> self-preference, position bias), and the "Show Your Work" / reproducibility-checklist
> reporting norms — reframed to audit a *third party's* evaluation design and reporting.
> A result can be arithmetically self-consistent (family A), run real code against a real
> ground truth (family D), and **still not measure what it claims**: the evaluation
> protocol leaks, the load-bearing metric is a conflicted/unvalidated LLM judge, or the
> reporting silently drops a condition the setup declared. **Distinct from family D:**
> family D is an L2-only code/result-integrity audit ("is the number what the code
> computed?"); family H is a **stated-tell** decided from the *described protocol* at
> L0/L1 ("is what it measured a valid measurement of the claim?"), which a repo then
> *confirms* at L2 — the "stated → verified" profile of family C, not the L2-only profile
> of family D. They **can be critical**: a leaked split or a conflicted judge can make the
> headline number meaningless. Owned by `skills/eval-design-forensics` → adjudicator
> dimension `evaluation`. Three subtypes are **not decidable from the PDF or even the
> repo** — an illegitimate-proxy feature, sampling bias in the test set, and
> pretraining/benchmark contamination of an evaluated model — so they hand off as
> `needs_external_check` (the adjudicator pins them to `info`; we name the external
> methods, we do not run them). STRICT framing: leakage and incomplete reporting are most
> often **honest methodological errors** — every finding asks a reviewer to *check/clarify*
> the protocol, it **never** alleges the authors cheated. High-FP care: the absence of a
> *reported* validation is not proof none was done; cite the exact protocol span that fails.

### HP-EVAL-LEAKAGE — train/test leakage means the reported score may not measure generalization
- **level:** L0 (stated — the described protocol reveals the leak) / L2 (verified against the
  split files + preprocessing code); the **illegitimate-proxy feature**, **sampling-bias**, and
  **pretraining-contamination** subtypes → `needs_external_check` (domain / black-box judgment).
- **framing note:** adopts the eight-type leakage taxonomy of Kapoor & Narayanan (2023),
  paraphrasing their three category labels. **Their leakage-*type* L1/L2/L3 are NOT this repo's
  observability L0/L1/L2** — keep the two scales separate in every finding.
- **signals:** the evaluation, as described (L0) or as built (L2), admits one of the eight leakage
  types: *K&N L1 — no clean train/test separation* (no held-out test; preprocessing or
  feature-selection fit before the split; duplicates across splits) → L0 stated / L2 verified;
  *K&N L2 — illegitimate (proxy) feature* → needs_external_check; *K&N L3 — test not from the
  distribution of interest* (temporal leakage / non-independence e.g. same subject in both splits
  → L0 stated / L2 verified; sampling bias → needs_external_check); *pretraining/benchmark
  contamination of an evaluated LLM* → needs_external_check (name the external methods — Oren 2023
  exchangeability, Shi 2023 Min-K%, Golchin 2023 Time-Travel, BIG-bench canary — never run them).
- **fp_cases:** a transductive/semi-supervised design where overlap is intended and declared; a
  standard fixed benchmark split; a genuinely-available "proxy-looking" feature; a correctly
  time-respecting split; a benchmark released after the model's cutoff or a corpus documented to
  exclude it; preprocessing fit on **train only** then applied to test (the correct pattern).
- **severity_rule:** critical if the leak plausibly invalidates the headline generalization claim
  and the tell is unambiguous (`false_positive_risk: low`); major if non-headline; the proxy /
  sampling-bias / contamination subtypes are `needs_external_check` (pinned to info). Never grade
  leakage as fabrication — it is a methodological discrepancy to clarify.
- **min_evidence:** the protocol/split/preprocessing-description span (the ledger claim it
  undermines) + which of the eight types it matches (L0); the split-file/code confirmation (L2).
- **example:** "We standardize all features, then split 80/20." → the scaler is fit on the test
  rows (K&N L1), so the reported accuracy may not reflect generalization — ask whether it was fit
  on train only.
- **ack:** Kapoor & Narayanan, "Leakage and the reproducibility crisis in ML-based science,"
  *Patterns* 2023 — the 8 leakage types / 3 categories, paraphrased (**priority ack**). Contamination
  methods named only: Oren 2023; Shi 2023; Golchin & Surdeanu 2023; BIG-bench (Srivastava 2022).

### HP-JUDGE-VALIDITY — the load-bearing metric is an LLM judge that is conflicted or unvalidated
- **level:** L0/L1 (stated — read off the described eval protocol: which model is the judge, and
  whether any human-agreement validation / bias control is reported).
- **framing note:** scope is the LLM-as-**judge** — its preference/score IS the reported metric. An
  LLM that generates the GROUND-TRUTH labels/targets is **HP-FAKE-GT** (family D, L2) — route there.
- **signals:** a headline comparison rests on an automatic LLM judge, and either — *conflicted:* the
  judge is the same model/family as a compared system (especially the proposed one), so its
  preference is the evidence (self-enhancement / self-preference); or *unvalidated:* the LLM judge is
  load-bearing yet the paper reports no human-agreement validation (no correlation/κ vs humans) and
  no bias control (no position-swap, no length/verbosity control).
- **fp_cases:** the judge is validated against human agreement and bias controls are reported; the
  judge is a clearly different family from every compared system AND corroborated by human eval /
  standard metrics (not load-bearing); a well-established calibrated judge protocol. **Unvalidated-only
  is high-FP:** missing validation *reporting* is not proof none was done.
- **severity_rule:** major if a headline rests on the judge — *conflicted* is the lower-FP structural
  case (judge-family == compared-system-family is checkable: `false_positive_risk: medium` → caps at
  major); *unvalidated-only* is `false_positive_risk: high` → caps at minor. Minor if not load-bearing.
- **min_evidence:** the judge-protocol span naming the judge model + the compared-systems span showing
  the family overlap (conflicted) OR the absence of any reported human-agreement / bias-control
  (unvalidated) + the headline claim it supports.
- **example:** "We use GPT-4 as a judge to score our GPT-4-based agent vs baselines; ours wins 78%."
  → judge shares a family with the proposed system (conflicted) and no human-agreement number is given.
- **ack:** Zheng et al. 2023 (MT-Bench — self-enhancement + the human-agreement bar); Panickssery et
  al. 2024 (self-preference); Wang et al. 2024 (position bias in LLM evaluators).

### HP-SELECTIVE-REPORTING — a declared condition is dropped, or the metric switched, to favor the method
- **level:** L0 (stated — the setup declares a condition the results/appendix do not report) / L2
  (verified — the result files show the condition ran but was not reported).
- **signals:** one of — a dataset/baseline/metric/seed-count the **setup explicitly declares** then
  omitted from the results and absent from the appendix; metric-switching across tables in a way that
  consistently favors the proposed method; "we report the best checkpoint/prompt/run" with **no
  held-out selection set** (selecting on the test set).
- **fp_cases:** a declared condition omitted but explicitly justified ("full grid in the repo");
  different tasks legitimately using different standard metrics; best-checkpoint selection on a
  *declared held-out validation* set; an honestly-labeled preliminary/pilot result.
- **severity_rule:** major; critical if the omission/switch/selection is what produces the headline
  (`false_positive_risk: low` when the declared-vs-reported gap is unambiguous); minor if peripheral.
- **min_evidence:** the setup-declaration span (what was promised) + the results span where it is
  absent (and confirmation it is not in the appendix); for metric-switching, the two table spans; at
  L2, the result file showing the condition ran but went unreported.
- **example:** the setup says "We evaluate on five datasets {A,B,C,D,E}" but every table reports only
  {A,B,C} with no appendix for D,E. **De-dup:** best-reported-as-mean → HP-AGG-DRIFT (A); thin scope →
  HP-SCOPE-INFLATE (B); a never-mentioned expected baseline → HP-MISSING-BASELINE (C); appendix-vs-main
  on the *same* quantity → HP-APPENDIX-CONTRA (A). Scoped to declared-but-unreported / cherry-picked-among-shown.
- **ack:** Dodge et al. 2019 ("Show Your Work"); Pineau et al. 2021 (ML Reproducibility Checklist).

## Advisory signals (NOT a hard pattern · zero verdict weight · reviewer-judgment only)

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
