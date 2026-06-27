#!/usr/bin/env python3
"""
check_stat_consistency.py — deterministic statistical-consistency checks (family A).

Three model-free, arithmetic-only forensics over the evidence ledger. Like
check_numeric_consistency.py, these need NO language model: they emit findings.json
(schemas/finding.schema.json) with reviewer.deterministic=true, are span-anchored,
and form part of the eval-gated deterministic core consumed by adjudicate_findings.py.

  HP-GRANULARITY-IMPOSSIBLE (GRIM) — a proportion/accuracy reported over an integer
      item count N cannot equal round(k/N) at the stated precision for ANY integer k
      ("84.7% on 500 items" is impossible: 0.2*423=84.6, 0.2*424=84.8).
      Paraphrased from the GRIM test (Brown & Heathers, 2017); ref impl `scrutiny`
      (Jung, MIT). No GPL code copied.
  HP-VARIANCE-IMPOSSIBLE (GRIMMER + Bhatia-Davis) — a reported SD exceeds the largest
      SD a bounded metric can have at the reported mean: for a metric in [a,b],
      Var <= (b-mu)(mu-a) (Bhatia-Davis), SD <= (b-a)/2 (Popoviciu), with the sample
      (Bessel) correction applied when N is known. Paraphrased from GRIMMER (Anaya,
      2016) + the Bhatia-Davis inequality.
  HP-STAT-INCONSISTENCY (statcheck) — the p-value recomputed from a reported test
      statistic + df contradicts the reported p, AND the .05 decision flips. z-tests
      use the stdlib statistics.NormalDist; t / F / chi2 / r use an OPTIONAL scipy
      backend (import-guarded — scipy is NOT a core dependency; if absent we run
      z-only and record the backend in each finding's provenance). Concept paraphrased
      from statcheck (Nuijten & Epskamp); statcheck itself is GPL-3 and is credited by
      name only — none of its code is reused. FP taxonomy informed by the statcheck
      critique (arXiv:2408.07948).

DOCTRINE: a checkable discrepancy, never an accusation. Decidable at L0 (text). These
checks are conservative and low-FP by design (they join the eval-gated core, so a
false positive is a real bug): a finding is escalated to major/critical only when a
significance or headline conclusion would flip; otherwise it is minor/info.
"""
import argparse
import json
import math
import re
import sys
from statistics import NormalDist

try:  # OPTIONAL backend — t / F / chi2 / r only. scipy is NOT a core dependency.
    from scipy import stats as _scipy_stats
    _HAS_SCIPY = True
except Exception:  # pragma: no cover - environment dependent
    _scipy_stats = None
    _HAS_SCIPY = False

_NORMAL = NormalDist()
ALPHA = 0.05


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _norm(span):
    """Match against text the way it reads, but the EVIDENCE span we emit is always
    the raw ledger text_span (so it anchors verbatim against the ledger claim)."""
    return span.replace("\\%", "%").replace("\\,", " ").replace("~", " ")


def _decimals(num_str):
    """Fractional digits in the literal as written (its display precision)."""
    return len(num_str.split(".", 1)[1]) if "." in num_str else 0


def _section_headline(section):
    s = section or ""
    return any(k in s for k in ("abstract", "intro", "conclusion"))


# --------------------------------------------------------------------------- #
# 1. HP-GRANULARITY-IMPOSSIBLE (GRIM)
# --------------------------------------------------------------------------- #
# A proportion the GRIM test applies to: a count of successes over N integer items.
# Whitelisted count-proportion contexts ONLY; non-count metrics (F1/AUC/BLEU/ROUGE/
# perplexity/MSE/...) are NOT k/N and are excluded (taxonomy fp_cases).
GRIM_METRIC = re.compile(
    r"\b(accuracy|acc|correct(?:ly)?|success(?:\s*rate)?|error\s*rate|"
    r"exact\s*match|EM|solved|passed|pass\s*rate|win[- ]?rate|"
    r"answered\s+correctly)\b", re.IGNORECASE)

# Item-count denominators. Note: 'seeds|runs|epochs|models|datasets|tasks' are
# deliberately ABSENT — a percentage "over 5 seeds" is a MEAN over seeds, not k/5,
# so GRIM must not treat 5 as N (taxonomy fp: mean/SD over seeds vs over items).
GRIM_N = re.compile(
    r"N\s*=\s*(\d{1,7})\b"
    r"|\b(\d{1,7})\s*(?:-|\s)?(?:item|example|question|sample|instance|case|"
    r"problem|sentence|image|datapoint|document|prompt|query|trial)s?\b"
    r"|\b(?:test|eval(?:uation)?|held[- ]?out|dev|validation)\s*set\s*of\s*(\d{1,7})\b"
    r"|\bout\s+of\s+(\d{1,7})\b",
    re.IGNORECASE)

PCT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")

# A percent in an AGGREGATE or RELATIVE context is not a single k/N proportion, so GRIM
# does not apply — skip the whole span (codex FP review: macro/weighted/balanced means and
# "improved by X%" relative figures are legitimate non-GRIM values).
GRIM_EXCLUDE = re.compile(
    r"\b(macro|micro|weighted|balanced|harmonic|geometric|"
    r"improv\w*|increase\w*|decreas\w*|reduc\w*|\bgain\b|relative|"
    r"average\s+of|mean\s+(?:over|of|across)|averaged\s+(?:over|across))\b",
    re.IGNORECASE)


def _grim_vacuous(N, d):
    """When the granularity step (100/N points) is at/below the display resolution
    (10^-d), every displayed value is achievable -> the test is vacuous. Skip
    (taxonomy fp: large-N-where-granularity<rounding)."""
    return (100.0 / N) <= (10 ** (-d)) + 1e-12


def _grim_achievable(p, N, d):
    """True if percentage p (d decimals) equals round(100*k/N) for some integer k in
    [0,N]. 'rounds-to' is tested generously (within a half-ULP) so it covers half-up
    AND half-even rounding -> we flag ONLY when no integer k works under any standard
    rounding convention (keeps FP near zero)."""
    half_ulp = 0.5 * (10 ** (-d))
    target = p / 100.0 * N
    lo = max(0, math.floor(target) - 1)
    hi = min(N, math.ceil(target) + 1)
    return any(abs(100.0 * k / N - p) <= half_ulp + 1e-9 for k in range(lo, hi + 1))


def _grim_nearest(p, N, d):
    target = p / 100.0 * N
    best = None
    for k in (math.floor(target), round(target), math.ceil(target)):
        if 0 <= k <= N:
            v = round(100.0 * k / N, d)
            if best is None or abs(v - p) < abs(best - p):
                best = v
    return best


def check_grim(claims):
    findings, n, seen = [], 0, set()
    for c in claims:
        if c.get("type") not in ("number", "table_cell"):
            continue
        raw = c.get("text_span", "")
        span = _norm(raw)
        if not GRIM_METRIC.search(span):
            continue
        if GRIM_EXCLUDE.search(span):          # aggregate/relative % is not k/N -> skip (fp)
            continue
        Ns = sorted({int(g) for m in GRIM_N.finditer(span)
                     for g in m.groups() if g})
        if len(Ns) != 1:                       # 0 or ambiguous -> skip (fp)
            continue
        N = Ns[0]
        if N <= 0:
            continue
        for pm in PCT.finditer(span):
            pstr = pm.group(1)
            p = float(pstr)
            if not (0.0 < p <= 100.0):
                continue
            d = _decimals(pstr)
            if _grim_vacuous(N, d) or _grim_achievable(p, N, d):
                continue
            loc = c.get("location") or {}
            key = (loc.get("file"), loc.get("line"), pstr, N)
            if key in seen:
                continue
            seen.add(key)
            n += 1
            headline = _section_headline(loc.get("section"))
            near = _grim_nearest(p, N, d)
            findings.append({
                "finding_id": f"GRIM{n:03d}",
                "skill": "consistency-audit",
                "pattern_id": "HP-GRANULARITY-IMPOSSIBLE",
                "title": "Reported proportion is not achievable for the stated N",
                "description": (
                    f"{p:g}% over N={N} integer items is not round(k/{N}) at "
                    f"{d} decimal place(s) for any integer k "
                    f"(nearest achievable {near:g}%). The value, its precision, or N "
                    f"may be misreported, or trials may have been excluded."),
                "severity": "major" if headline else "minor",
                "observability_level_required": 0,
                "evidence": [{
                    "claim_id": c.get("claim_id", "?"),
                    "span": raw,
                    "location": loc,
                    "artifact_hash": c.get("evidence_anchor", ""),
                }],
                "verdict_local": "fail" if headline else "warn",
                "reviewer": {"deterministic": True, "method": "GRIM"},
                "false_positive_risk": "low",
                "recommended_reviewer_action": (
                    "Ask the authors to reconcile the value, its precision, and the "
                    "exact denominator N (e.g. excluded/invalid items, or a "
                    "macro/weighted average rather than a simple proportion)."),
            })
    return findings


# --------------------------------------------------------------------------- #
# 2. HP-VARIANCE-IMPOSSIBLE (GRIMMER + Bhatia-Davis)
# --------------------------------------------------------------------------- #
# Metrics with a known theoretical range (so a bound exists). Unbounded metrics are
# explicitly excluded (taxonomy fp: range not [0,1] -> loss/perplexity/MSE/...).
BOUNDED_METRIC = re.compile(
    r"\b(accuracy|acc|success\s*rate|error\s*rate|exact\s*match|EM|win[- ]?rate|"
    r"pass\s*rate|precision|recall|F1|F-?1|AUC|AUROC|AUPRC|IoU|mIoU|mAP|"
    r"coverage|agreement)\b", re.IGNORECASE)
UNBOUNDED_METRIC = re.compile(
    r"\b(loss|perplexity|PPL|MSE|RMSE|MAE|latency|throughput|runtime|FLOPs?|"
    r"reward|return|tokens?|steps?|epochs?|seconds?|minutes?|hours?)\b",
    re.IGNORECASE)
# A dispersion explicitly labeled SEM / standard error / CI / error-bar is NOT an SD
# -> skip (fp). We also REQUIRE an explicit SD label below: a bare "98% ± 12%" could be a
# CI/SEM, so we never flag it as an impossible SD (codex FP review).
SEM_LABEL = re.compile(r"\b(standard\s+error|std\.?\s*err\.?|SEM|S\.E\.)\b", re.IGNORECASE)
CI_LABEL = re.compile(r"\b(confidence\s+interval|\bCI\b|credible\s+interval|"
                      r"error\s*bars?|IQR|interquartile|range)\b", re.IGNORECASE)
SD_LABEL = re.compile(r"\b(standard\s+deviation|std\.?\s*dev\.?|std|SD)\b|σ",
                      re.IGNORECASE)
# sample size for the Bessel correction (here seeds/runs/trials ARE valid).
N_SAMPLE = re.compile(
    r"N\s*=\s*(\d{1,6})\b"
    r"|\b(\d{1,6})\s+(?:seeds?|runs?|trials?|folds?|repetitions?|replicates?|"
    r"experiments?|items?|examples?|samples?)\b", re.IGNORECASE)
SD_PATTERNS = [
    # mean (%) ± sd (%)
    re.compile(r"(\d+(?:\.\d+)?)\s*(%?)\s*(?:±|\\pm|\+/-|\+-)\s*"
               r"(\d+(?:\.\d+)?)\s*(%?)"),
    # mean (%) ... standard deviation [of|=|:] sd (%)
    re.compile(r"(\d+(?:\.\d+)?)\s*(%?)[^.;]{0,45}?"
               r"(?:standard\s+deviation|std\.?\s*dev\.?|\bSD\b|σ)"
               r"[^.;]{0,12}?(?:of|=|:|\s)\s*(\d+(?:\.\d+)?)\s*(%?)", re.IGNORECASE),
    # mean (%) (SD = sd (%))
    re.compile(r"(\d+(?:\.\d+)?)\s*(%?)\s*\(\s*(?:SD|std|σ)\s*[=:]?\s*"
               r"(\d+(?:\.\d+)?)\s*(%?)\s*\)", re.IGNORECASE),
]


def _sd_upper_bound(mu, a, b, n):
    """Largest SD a [a,b]-bounded variable can have at mean mu. Bhatia-Davis
    population bound sqrt((b-mu)(mu-a)), times the Bessel factor for the SAMPLE SD:
      n known (>=2): sqrt(n/(n-1))
      n unknown    : sqrt(2)   (the n=2 case — the MOST permissive bound, so we never
                                false-positive on a larger sample whose n we didn't see)
    Returns None when mu is out of [a,b] (a different problem) or n<2."""
    if not (a <= mu <= b):
        return None
    pop = math.sqrt(max(0.0, (b - mu) * (mu - a)))
    if n is None:
        factor = math.sqrt(2.0)
    elif n >= 2:
        factor = math.sqrt(n / (n - 1.0))
    else:
        return None
    return pop * factor


def check_variance(claims):
    findings, n_id, seen = [], 0, set()
    for c in claims:
        if c.get("type") not in ("number", "table_cell"):
            continue
        raw = c.get("text_span", "")
        span = _norm(raw)
        if not BOUNDED_METRIC.search(span) or UNBOUNDED_METRIC.search(span):
            continue
        if SEM_LABEL.search(span) or CI_LABEL.search(span):   # SEM / CI / error-bar is not SD (fp)
            continue
        explicit_sd = bool(SD_LABEL.search(span))
        if not explicit_sd:                    # require an explicit SD label — a bare ± may be CI/SEM (fp)
            continue
        Nn = None
        nm = N_SAMPLE.search(span)
        if nm:
            g = next((x for x in nm.groups() if x), None)
            Nn = int(g) if g else None
        for pat in SD_PATTERNS:
            for m in pat.finditer(span):
                mean_s, mean_u, sd_s, sd_u = m.group(1), m.group(2), m.group(3), m.group(4)
                mu, s = float(mean_s), float(sd_s)
                is_pct = ("%" in (mean_u or "")) or ("%" in (sd_u or ""))
                if is_pct:
                    a, b = 0.0, 100.0
                elif 0.0 <= mu <= 1.0:         # bare fraction proportion
                    a, b = 0.0, 1.0
                else:
                    continue                   # unknown / unbounded scale -> skip (fp)
                # Max bound over the mean's DISPLAYED rounding interval [mu-h, mu+h] ∩ [a,b].
                # The Bhatia-Davis bound is nonlinear with unbounded slope near a/b, so
                # evaluating only at the displayed mu false-positives near the edges (codex):
                # a displayed mean of 0.0% admits a true mean up to 0.05% whose attainable SD
                # is > 0. The bound is maximized at the interval point nearest the midpoint.
                h_mu = 0.5 * 10 ** (-_decimals(mean_s))
                mu_lo, mu_hi = max(a, mu - h_mu), min(b, mu + h_mu)
                if mu_lo > mu_hi:              # mean outside [a,b] beyond rounding -> skip
                    continue
                mu_worst = min(max((a + b) / 2.0, mu_lo), mu_hi)
                bound = _sd_upper_bound(mu_worst, a, b, Nn)
                if bound is None:
                    continue
                sd_half_ulp = 0.5 * 10 ** (-_decimals(sd_s))
                if s - sd_half_ulp <= bound + 1e-9:   # reported SD (less its rounding) vs max bound
                    continue
                loc = c.get("location") or {}
                key = (loc.get("file"), loc.get("line"), mean_s, sd_s)
                if key in seen:
                    continue
                seen.add(key)
                n_id += 1
                rng = "[0,100] (%)" if is_pct else "[0,1]"
                nnote = f"sample n={Nn}" if Nn else "n unknown, n=2 (most permissive) bound"
                findings.append({
                    "finding_id": f"VAR{n_id:03d}",
                    "skill": "consistency-audit",
                    "pattern_id": "HP-VARIANCE-IMPOSSIBLE",
                    "title": "Reported SD exceeds the maximum possible for a bounded metric",
                    "description": (
                        f"SD {s:g} is reported at mean {mu:g} for a metric bounded in "
                        f"{rng}; the largest attainable SD there is {bound:.3g} "
                        f"(Bhatia-Davis, {nnote}). The SD, the mean, the metric range, "
                        f"or an SD-vs-SEM label may be misreported."),
                    "severity": "major",
                    "observability_level_required": 0,
                    "evidence": [{
                        "claim_id": c.get("claim_id", "?"),
                        "span": raw,
                        "location": loc,
                        "artifact_hash": c.get("evidence_anchor", ""),
                    }],
                    "verdict_local": "fail",
                    "reviewer": {"deterministic": True, "method": "Bhatia-Davis/Popoviciu"},
                    "false_positive_risk": "low" if (Nn and explicit_sd) else "medium",
                    "recommended_reviewer_action": (
                        "Confirm the dispersion is a standard deviation (not SEM/CI), "
                        "that mean and SD share a scale, the metric's true range, and "
                        "the sample size used for the variance."),
                })
    return findings


# --------------------------------------------------------------------------- #
# 3. HP-STAT-INCONSISTENCY (statcheck)
# --------------------------------------------------------------------------- #
# z = 2.10, p = .03 | t(28) = 2.1, p = 0.04 | F(1, 28) = 4.5, p = .04 |
# chi2(1) = 3.9, p = .048 | r(30) = .42, p = .02
STAT_RX = re.compile(
    r"\b(?P<kind>z|t|F|r|chi2|chi\^?2|χ\^?2|χ\xb2)\s*"
    r"(?:\(\s*(?P<df1>\d+(?:\.\d+)?)\s*(?:,\s*(?P<df2>\d+(?:\.\d+)?)\s*)?\))?\s*"
    r"=\s*(?P<stat>-?\d+(?:\.\d+)?)\s*[,;]\s*"
    r"p\s*(?P<rel>[<>=])\s*(?P<pval>\d?\.\d+)",
    re.IGNORECASE)


def _sf_z(x):
    return 1.0 - _NORMAL.cdf(x)               # upper-tail of the standard normal


def _p_bounds(kind, stat_str, df1, df2):
    """Return (two_lo, two_hi, one_lo, one_hi, backend) for the recomputed p, where
    the interval brackets the statistic's own rounding (|stat| +/- half-ULP); p is
    monotone-decreasing in |stat|, so +h gives the low p and -h the high p. Returns
    None when the backend for this test is unavailable (t/F/chi2/r without scipy)."""
    stat = float(stat_str)
    h = 0.5 * 10 ** (-_decimals(stat_str))
    x_hi = abs(stat) + h
    x_lo = max(0.0, abs(stat) - h)
    k = kind.lower()
    if "chi" in k or "χ" in kind:
        k = "chi2"
    if k == "z":
        return (2 * _sf_z(x_hi), 2 * _sf_z(x_lo), _sf_z(x_hi), _sf_z(x_lo),
                "stdlib-normaldist")
    if not _HAS_SCIPY:
        return None
    # adjusted/fractional df (Welch t, Greenhouse-Geisser F) cannot be reliably recomputed
    # from the rounded df alone -> skip rather than risk a false positive (codex FP review).
    for d in (df1, df2):
        if d is not None and "." in d and float(d) != int(float(d)):
            return None
    try:
        if k == "t":
            if df1 is None:
                return None
            df = float(df1)
            return (2 * _scipy_stats.t.sf(x_hi, df), 2 * _scipy_stats.t.sf(x_lo, df),
                    _scipy_stats.t.sf(x_hi, df), _scipy_stats.t.sf(x_lo, df), "scipy-t")
        if k == "r":
            if df1 is None:
                return None
            df = float(df1)

            def r2t(rv):
                rv = min(0.999999, abs(rv))
                return rv * math.sqrt(df / (1 - rv * rv))
            return (2 * _scipy_stats.t.sf(r2t(x_hi), df),
                    2 * _scipy_stats.t.sf(r2t(x_lo), df),
                    _scipy_stats.t.sf(r2t(x_hi), df),
                    _scipy_stats.t.sf(r2t(x_lo), df), "scipy-r")
        if k == "f":
            if df1 is None or df2 is None:
                return None
            d1, d2 = float(df1), float(df2)
            p_hi, p_lo = _scipy_stats.f.sf(x_hi, d1, d2), _scipy_stats.f.sf(x_lo, d1, d2)
            return (p_hi, p_lo, p_hi, p_lo, "scipy-f")     # one-sided: one==two
        if k == "chi2":
            if df1 is None:
                return None
            d1 = float(df1)
            p_hi, p_lo = _scipy_stats.chi2.sf(x_hi, d1), _scipy_stats.chi2.sf(x_lo, d1)
            return (p_hi, p_lo, p_hi, p_lo, "scipy-chi2")  # one-sided: one==two
    except Exception:
        return None
    return None


def _overlap(a_lo, a_hi, b_lo, b_hi):
    return not (a_hi < b_lo or b_hi < a_lo)


def check_statcheck(claims):
    findings, n, seen = [], 0, set()
    skipped_no_backend = 0
    for c in claims:
        if c.get("type") not in ("number", "table_cell"):
            continue
        raw = c.get("text_span", "")
        span = _norm(raw)
        for m in STAT_RX.finditer(span):
            kind = m.group("kind")
            stat_str = m.group("stat")
            df1, df2 = m.group("df1"), m.group("df2")
            rel, pstr = m.group("rel"), m.group("pval")
            bounds = _p_bounds(kind, stat_str, df1, df2)
            if bounds is None:                 # t/F/chi2/r and no scipy -> skip
                skipped_no_backend += 1
                continue
            two_lo, two_hi, one_lo, one_hi, backend = bounds
            pval = float(pstr)
            if rel == "=":
                hp = 0.5 * 10 ** (-_decimals(pstr))
                rlo, rhi = max(0.0, pval - hp), min(1.0, pval + hp)
            elif rel == "<":
                rlo, rhi = 0.0, pval
            else:                              # ">"
                rlo, rhi = pval, 1.0
            # Accept EITHER two-tailed OR one-tailed -> kills the #1 statcheck FP.
            if (_overlap(rlo, rhi, two_lo, two_hi)
                    or _overlap(rlo, rhi, one_lo, one_hi)):
                continue
            # inconsistent. Emit ONLY the FP-safe OVERSTATE case: the reported p claims
            # significance the statistic cannot support under ANY valid reading. The other
            # directions are deliberately NOT emitted in the deterministic core (codex FP
            # review): understate (claims ns but is significant) is dominated by legitimate
            # multiple-comparison / Bonferroni / FDR adjustment, and a same-side-of-.05
            # discrepancy doesn't change the decision — both are too FP-prone here. (An
            # adjustment only makes p LARGER, so it can never cause a false overstate.)
            report_sig = (rel == "=" and pval < ALPHA) or (rel == "<" and pval <= ALPHA)
            can_be_sig = min(one_lo, two_lo) < ALPHA     # significant under SOME valid reading
            overstate = report_sig and not can_be_sig
            if not overstate:
                continue
            loc = c.get("location") or {}
            key = (loc.get("file"), loc.get("line"), kind, stat_str, pstr)
            if key in seen:
                continue
            seen.add(key)
            headline = _section_headline(loc.get("section"))
            sev = "critical" if headline else "major"
            fpr = "medium"
            vl = "fail"
            why = "reported p claims significance the statistic does not support"
            n += 1
            findings.append({
                "finding_id": f"STAT{n:03d}",
                "skill": "consistency-audit",
                "pattern_id": "HP-STAT-INCONSISTENCY",
                "title": "Reported p-value is inconsistent with its test statistic",
                "description": (
                    f"Reported {kind}={float(stat_str):g}"
                    + (f", df={df1}" + (f",{df2}" if df2 else "") if df1 else "")
                    + f", p{rel}{pstr}; recomputed two-tailed p in "
                    f"[{two_lo:.4f},{two_hi:.4f}] (one-tailed [{one_lo:.4f},"
                    f"{one_hi:.4f}], backend {backend}). {why}. May reflect a "
                    f"one-tailed test, adjusted/Welch df, or a typo."),
                "severity": sev,
                "observability_level_required": 0,
                "evidence": [{
                    "claim_id": c.get("claim_id", "?"),
                    "span": raw,
                    "location": loc,
                    "artifact_hash": c.get("evidence_anchor", ""),
                }],
                "verdict_local": vl,
                "reviewer": {"deterministic": True, "method": "statcheck",
                             "backend": backend},
                "false_positive_risk": fpr,
                "recommended_reviewer_action": (
                    "Ask whether the test was one- or two-tailed, whether p was "
                    "multiplicity-adjusted, and whether the df/statistic are correct."),
            })
    return findings, skipped_no_backend


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic statistical-consistency checks.")
    ap.add_argument("--ledger", required=True, help="claims.json from build_claim_ledger.py")
    ap.add_argument("--out", default="consistency-audit.stat.findings.json")
    args = ap.parse_args(argv)

    with open(args.ledger, "r", encoding="utf-8") as fh:
        ledger = json.load(fh)
    claims = ledger.get("claims", [])

    grim = check_grim(claims)
    var = check_variance(claims)
    stat, skipped = check_statcheck(claims)
    findings = grim + var + stat
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2, ensure_ascii=False)
    backend = "scipy" if _HAS_SCIPY else "stdlib-z-only (scipy absent: t/F/chi2/r skipped)"
    print(f"stat findings: {len(findings)} "
          f"({len(grim)} grim, {len(var)} variance, {len(stat)} statcheck; "
          f"backend={backend}"
          + (f"; {skipped} stat tests skipped (no scipy)" if skipped else "")
          + f") -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
