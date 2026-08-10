#!/usr/bin/env python3
"""
adjudicate_findings.py — the deterministic reporter.

The structural defense against "LLM slop grading LLM slop": the language-model
auditors PROPOSE findings (each anchored to an evidence-ledger span); no model
ever writes a severity that this script then treats as authoritative, and no
model writes the summary. What this script does NOT do any more is decide, on
the model's behalf, which of its proposals do not count.

Two rules still move a severity, and both act on the ACCUSATION rather than on
the paper:
  ANCHOR — an above-info finding whose quoted span is not in the ledger (or any
           finding when no ledger is given) drops to info and is reported as
           unanchored. That the span is absent from the paper is a fact a
           computation establishes.
  CRITICAL SCRUTINY (apply_critical_scrutiny, further down) — a critical that does
           not declare an alternative explanation, or whose numeric_basis is
           missing or malformed, drops to major. That is not a judgement about the
           paper: it limits an accusation whose own basis cannot be re-checked.

Everything else is recorded beside the finding, for the human:
  _observability_required / _observability_met   what level the auditor said it needs
  _fp_risk                                       the auditor's own false-positive estimate
  _surface_signal                                family-F presentation class
  _needs_external_check                          the auditor marked it unsettled
  _verdict_weight = 0                            AIS / advisory memos, reported separately

Those four used to demote. Three of them read fields the AUDITOR supplies about
its own output — false_positive_risk is literally an "honest self-assessment" in
finding.schema.json — so demoting on them let a model's opinion of itself change
severity through a rule that only looked deterministic.

Summary rule (over weight-1 findings):
  any critical                 -> HARD_FLAGS
  else any major/minor         -> SOFT_FLAGS
  else                         -> CLEAN_GIVEN_EVIDENCE   (NOT "the paper is honest")
The summary reports what the auditors PROPOSED, computed by a fixed rule. It is
not an adjudication that those proposals stand — a human reads the table.

Pure standard library. See references/{reviewer-independence,observability-levels,
integrity-forensics-contract}.md.
"""
import argparse
import datetime
import json
import os
import sys

REPORT_VERSION = "0.5"  # v0.5: dropped v0.4's self-binding hashes — nothing consumed them; v0.3: critical_countercheck
ADJUDICATOR_ID = "deterministic-rules-v2"  # v2: deterministic counter-check resolvers (issue #15); v1: critical scrutiny

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from countercheck import (ALLOWLIST as CC_ALLOWLIST, PROVED_COMPATIBLE,  # noqa: E402
                          delta_convention, display_precision,
                          rounding_interval_delta)

SEV_ORDER = {"info": 0, "minor": 1, "major": 2, "critical": 3}
SEV_NAME = {v: k for k, v in SEV_ORDER.items()}

SKILL_TO_DIMENSION = {
    "consistency-audit": "consistency",
    "experiment-forensics": "experiment",
    "baseline-comparison-audit": "baseline",
    "citation-forensics": "citation",
    "presentation-signals": "presentation",
    "proof-derivation-forensics": "proof",
    "eval-design-forensics": "evaluation",
}
# ZERO verdict weight: advisory memos AND the AI writing-style impression track (AIS).
# These are REPORTED (AIS in its own report section) but can NEVER move the integrity
# verdict — they are forced to info here AND excluded from the verdict computation. A paper
# can be integrity-CLEAN while carrying a long AIS list. Enforced three ways (emitting skill,
# pattern PREFIX, and the deprecated-id set) so a zero-weight finding smuggled in under
# another skill/severity is still neutralized. See references/hack-pattern-taxonomy.md (AIS).
ZERO_WEIGHT_SKILLS = {"adversarial-case-builder", "novelty-duplication-advisory",
                      "ai-style-impressions"}
ZERO_WEIGHT_PREFIXES = ("ADV-", "AIS-")
# Style ids MIGRATED to the AIS track in v0.5; kept as deprecated aliases but forced
# zero-weight so an old findings.json cannot still push them to SOFT_FLAGS.
DEPRECATED_STYLE_PATTERNS = {"HP-AI-FLAVOR", "HP-DEFENSIVE-HEDGE", "HP-NARRATIVE-ARC-BREAK",
                             "HP-JARGON-STUFF", "HP-INVENTED-CODENAME"}
# Family F (still verdict-bearing surface): weak + high-FP, capped at minor so they
# contribute at most SOFT_FLAGS, never HARD_FLAGS. The pure-style signals USED to live here
# but moved to the zero-weight AIS track (above); what remains is checkable-ish presentation.
SURFACE_ONLY_SKILLS = {"presentation-signals"}
SURFACE_PATTERNS = {"HP-DUP-TABLE", "HP-THIN-FLOAT", "HP-LLM-FIGURE",
                    "HP-PAGE-PADDING", "HP-PIPELINE-ARTIFACT"}
FP_CAP = {"high": "minor", "medium": "major", "low": "critical"}


def _is_zero_weight(f):
    """A finding that must never move the integrity verdict (advisory memo or AI-style
    impression). Checked by emitting skill, pattern_id PREFIX, and the deprecated-style set."""
    pid = f.get("pattern_id")
    pid = pid.strip() if isinstance(pid, str) else ""   # tolerate dirty JSON trailing space
    return (f.get("skill") in ZERO_WEIGHT_SKILLS
            or pid.startswith(ZERO_WEIGHT_PREFIXES)
            or pid in DEPRECATED_STYLE_PATTERNS)


def _is_ais(f):
    """An AI writing-style IMPRESSION (the zero-weight AIS track), as distinct from an ADV
    advisory memo — used to render the separate, clearly-non-integrity AIS report section."""
    pid = f.get("pattern_id")
    pid = pid.strip() if isinstance(pid, str) else ""
    return (f.get("skill") == "ai-style-impressions"
            or pid.startswith("AIS-") or pid in DEPRECATED_STYLE_PATTERNS)


def _cap(sev, cap):
    """Return the lower of sev and cap (by severity order)."""
    return sev if SEV_ORDER[sev] <= SEV_ORDER[cap] else cap


def _norm_ws(s):
    # A non-str span/claim (e.g. a stray JSON number/null) -> "" so it can never anchor.
    if not isinstance(s, str):
        return ""
    return " ".join(s.split())


def _anchorable(span):
    """A span is specific enough to ANCHOR a flag only if it carries real content and
    is not a trivial substring of almost any claim. Blocks the 1-char / pure-punctuation
    "span" an auditor could staple onto a real claim_id to fake an anchor and reach a
    HARD verdict. Requires >=1 alphanumeric AND (>=12 chars OR >=3 word tokens). All
    real deterministic checkers emit full-sentence spans, so this never demotes them."""
    if not any(c.isalnum() for c in span):
        return False
    return len(span) >= 12 or len(span.split()) >= 3


def _anchored(finding, ledger_map):
    """True iff some evidence cites a real ledger claim_id AND quotes a span that is
    a verbatim (whitespace-normalized) substring OF that claim's text. Only `span in
    base` is allowed — NOT `base in span` — so appending hallucinated text to a real
    claim cannot pass. This is what makes the span gate a real anchor check rather
    than a string-presence check: an LLM cannot fabricate or pad its way to a flag."""
    for ev in finding.get("evidence", []) or []:
        cid = ev.get("claim_id")
        span = _norm_ws(ev.get("span"))
        if not cid or not _anchorable(span):
            continue
        base = ledger_map.get(cid)
        if base is None:
            continue
        if span in _norm_ws(base):
            return True
    return False


def load_findings(paths):
    findings = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        items = data.get("findings", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            print(f"WARN: {p} has no findings array; skipped", file=sys.stderr)
            continue
        for it in items:
            if not isinstance(it, dict):
                print(f"WARN: {p} has a non-object finding; skipped", file=sys.stderr)
                continue
            it.setdefault("_source_file", p)
            findings.append(it)
    return findings


def _is_llm_critical(f):
    """Refutation-eligible: a weight-1 critical proposed by an LLM reviewer.
    Deterministic findings are computed, not argued — nothing to refute.
    STRICT `is True`: reviewer provenance is model-influenced text, so anything
    other than the executor-written boolean (e.g. "false", 1, {}) is treated as
    NOT deterministic — fail-closed toward the gate applying."""
    rev = f.get("reviewer")
    is_det = isinstance(rev, dict) and rev.get("deterministic") is True
    return (f.get("_severity_final") == "critical"
            and f.get("_verdict_weight", 1) == 1
            and not is_det)


def _alt_explanation_ok(f):
    """The alternative_explanation_checked field must be a real string with
    substance (whitespace-normalized ≥ 20 chars) — `true`, `1`, "x", or an
    object is a gamed placeholder, not a ruled-out-alternatives record."""
    v = f.get("alternative_explanation_checked")
    return isinstance(v, str) and len(_norm_ws(v)) >= 20


def _refutation_counter_anchored(refutation, ledger_map):
    """A refutation only counts as CHECKABLE when at least one counter-evidence
    entry quotes a verbatim span of a real ledger claim — same `span in base`
    rule as findings (an opinion is not a counter-anchor)."""
    if not ledger_map:
        return False
    for ev in refutation.get("counter_evidence", []) or []:
        if not isinstance(ev, dict):
            continue
        cid = ev.get("claim_id")
        span = _norm_ws(ev.get("span"))
        if not cid or not _anchorable(span):
            continue
        base = ledger_map.get(cid)
        if base is not None and span in _norm_ws(base):
            return True
    return False


def _valid_numeric_basis(f, ledger_values):
    """The frozen computational basis of an allow-listed numeric accusation.
    Valid iff: list of {claim_id, role} dicts; roles are EXACTLY the resolver's
    required set (no dupes); every claim_id is cited in the finding's own evidence;
    every cited claim resolves to a parsed numeric ledger value; and the basis is
    COMPLETE — every numeric claim in the evidence appears in the basis (a basis
    that cherry-picks a compatible subset is invalid). Returns {role: claim_id}
    or None."""
    _resolver, roles_needed, _demotable = CC_ALLOWLIST[f.get("pattern_id")]
    basis = f.get("numeric_basis")
    if not isinstance(basis, list) or not all(isinstance(b, dict) for b in basis):
        return None
    roles = [b.get("role") for b in basis]
    ids = [b.get("claim_id") for b in basis]
    # dirty inputs fail CLOSED to basis-invalid, never crash (e.g. role: ["old"])
    if not all(isinstance(x, str) for x in roles + ids):
        return None
    if len(set(roles)) != len(roles) or len(set(ids)) != len(ids):
        return None
    if set(roles) != set(roles_needed):
        return None
    ev_ids = {e.get("claim_id") for e in (f.get("evidence") or []) if isinstance(e, dict)}
    if not set(ids) <= ev_ids:
        return None
    lv = ledger_values or {}
    # defense-in-depth (main() already filters, but direct callers must not crash):
    # every basis claim needs a plain-string raw display value to compute over
    if any(cid not in lv or not isinstance(lv[cid], dict)
           or not isinstance(lv[cid].get("raw"), str) for cid in ids):
        return None
    numeric_ev = {cid for cid in ev_ids if cid in (ledger_values or {})}
    if set(ids) != numeric_ev:
        return None
    return {b["role"]: b["claim_id"] for b in basis}


def _run_countercheck(f, role_map, ledger_values, ledger_map):
    """Execute the pattern's resolver on LEDGER-DERIVED values only. Returns
    (status, evidence) — the caller applies the fixed demotion rule."""
    resolver, _roles, _demotable = CC_ALLOWLIST[f.get("pattern_id")]
    vals = {r: ledger_values[cid] for r, cid in role_map.items()}
    if resolver == "rounding_interval":
        stated = vals["stated"]
        stated_span = (ledger_map or {}).get(role_map["stated"], "")
        convention = delta_convention(stated.get("unit"), stated_span, stated.get("raw"))
        return rounding_interval_delta(
            vals["old"]["raw"], vals["new"]["raw"], stated["raw"], convention,
            old_unit=vals["old"].get("unit"), new_unit=vals["new"].get("unit"),
            stated_unit=stated.get("unit"))
    return display_precision(
        vals["fine"]["raw"], vals["coarse"]["raw"],
        a_unit=vals["fine"].get("unit"), b_unit=vals["coarse"].get("unit"))


def apply_critical_scrutiny(findings, ledger_map=None, ledger_values=None):
    """Post-gate passes for LLM-proposed criticals (order matters; both are FIXED
    rules — no model output ever changes a verdict here):

    1. ALTERNATIVE-EXPLANATION gate (fail-closed): anchoring proves the quoted text
       exists, not that the reviewer's interpretation of it is right. A critical
       whose reviewer did not record what alternatives it ruled out
       (`alternative_explanation_checked`) demotes to major.
    2. CONTESTED marking (never severity-moving): a completed refutation attempt
       that claims refuted=true AND cites a checkable counter-anchor marks the
       finding `_contested` — the severity and the verdict stay untouched
       (the refuter is same-family adversarial REDUNDANCY, not a judge; the marker
       is for the human). All other refutation outcomes only leave audit notes.

    Returns the critical_refutation_coverage counters for the report."""
    cov = {"eligible": 0, "completed": 0, "unavailable": 0, "malformed": 0,
           "contested": 0}
    cc = {"eligible": 0, "proved_compatible": 0, "informational": 0,
          "discrepancy_persists": 0, "unresolvable": 0, "basis_invalid": 0}
    for f in findings:
        reasons = f.setdefault("_adjudication", [])
        # -- derive markers fresh every round: never trust input --
        f.pop("_contested", None)
        f.pop("_deterministic_countercheck", None)
        # -- gate 1: alternative_explanation_checked required on LLM criticals --
        if _is_llm_critical(f) and not _alt_explanation_ok(f):
            f["_severity_final"] = "major"
            reasons.append("alternative-explanation-not-declared")
        # -- gate 1b + deterministic counter-check (allow-listed numeric patterns) --
        # Runs UNCONDITIONALLY on eligible criticals — no model proposes or triggers
        # it (doctrine: only computations change severity, so the trigger path must
        # be model-free too). The accusation must freeze its computational basis at
        # creation; an accuser that omits or mangles the basis loses critical status
        # (fail-closed: an unauditable numeric accusation may not be a HARD flag).
        if _is_llm_critical(f) and f.get("pattern_id") in CC_ALLOWLIST:
            cc["eligible"] += 1
            role_map = _valid_numeric_basis(f, ledger_values or {})
            if role_map is None:
                cc["basis_invalid"] += 1
                f["_severity_final"] = "major"
                reasons.append("numeric-basis-not-declared-or-invalid")
            else:
                _res, _rr, demotable = CC_ALLOWLIST[f.get("pattern_id")]
                status, cc_ev = _run_countercheck(f, role_map, ledger_values or {},
                                                  ledger_map or {})
                f["_deterministic_countercheck"] = {"status": status, **cc_ev}
                if status == PROVED_COMPATIBLE and demotable:
                    cc["proved_compatible"] += 1
                    f["_severity_final"] = "info"
                    reasons.append("critical-basis-removed-by-deterministic-countercheck")
                elif status == PROVED_COMPATIBLE:
                    # binding-variant resolver (delta): the computation's verdict
                    # depends on model-assigned roles, so it may INFORM but never
                    # demote — recorded for the human, severity untouched.
                    cc["informational"] += 1
                    reasons.append("countercheck-informational-only (model-bound roles)")
                elif status == "DISCREPANCY_PERSISTS":
                    cc["discrepancy_persists"] += 1
                    reasons.append("countercheck-discrepancy-persists")
                else:
                    cc["unresolvable"] += 1
                    reasons.append("countercheck-unresolvable")
        # -- pass 2: contested marking on the criticals that remain --
        if not _is_llm_critical(f):
            continue
        cov["eligible"] += 1
        ref = f.get("refutation")
        if not isinstance(ref, dict) or ref.get("attempt_status") in (None, "", "unavailable"):
            cov["unavailable"] += 1
            continue
        # STRICT completed: exact status + well-typed payload; anything else —
        # unknown status, missing/non-bool refuted, wrong-typed fields — is
        # malformed, so a hollow {"attempt_status": "completed"} can never
        # silence the incomplete-pass limitation.
        ce = ref.get("counter_evidence")
        well_formed = (ref.get("attempt_status") == "completed"
                       and isinstance(ref.get("refuted"), bool)
                       and isinstance(ref.get("reason"), str)
                       and isinstance(ce, list)
                       and all(isinstance(e, dict) for e in ce))
        if not well_formed:
            cov["malformed"] += 1
            continue
        cov["completed"] += 1
        if ref.get("refuted") is True:
            if _refutation_counter_anchored(ref, ledger_map or {}):
                f["_contested"] = True
                reasons.append("contested-by-anchored-adversarial-pass")
                cov["contested"] += 1
            else:
                reasons.append("unanchored-refutation-claim")
        else:
            reasons.append("adversarial-refutation-not-found")
    cov["countercheck"] = cc
    return cov


def adjudicate(findings, run_level, ledger_map=None):
    """Annotate each finding; move severity only where a COMPUTATION licenses it.

    One rule still moves severity: ANCHOR. An above-info finding whose quoted span
    is not in the ledger is a span the auditor did not actually find in the paper,
    which is a fact a computation establishes, so it drops to info and is reported
    as unanchored.

    Everything else annotates. Observability, false-positive risk and
    needs-external-check are fields the AUDITOR supplies about its own output —
    false_positive_risk is described in finding.schema.json as an "honest
    self-assessment". Demoting on them let a model's opinion of itself change
    severity through a rule that merely looked deterministic. They are now recorded
    beside the finding for the human who reads the report.

    Zero-weight (AIS / advisory memos) and surface-only presentation signals stay
    categorical: they are decided by skill and pattern id, not by anything a model
    asserts, and they say what KIND of signal this is rather than how bad it is.
    """
    stats = {"downgraded_obs": 0, "unanchored": 0}
    for f in findings:
        original = f.get("severity", "info")
        if original not in SEV_ORDER:
            original = "info"
        sev = original
        reasons = []

        # ANCHOR/SPAN gate — the one computation that still moves severity.
        # Evaluated for EVERY finding so the column is honest about info-level ones
        # too; no ledger => nothing can be anchored => fail closed.
        is_anchored = bool(ledger_map) and _anchored(f, ledger_map)
        f["_anchored"] = is_anchored
        if SEV_ORDER[sev] > SEV_ORDER["info"] and not is_anchored:
            sev = "info"
            reasons.append("no-ledger-fail-closed" if ledger_map is None else "unanchored-demotion")
            stats["unanchored"] += 1

        # OBSERVABILITY — annotation. type(req) is int (NOT isinstance) so JSON
        # booleans (True == 1) are still rejected as undeclared.
        req = f.get("observability_level_required")
        if type(req) is not int or req < 0 or req > 3:
            f["_observability_required"] = None
            f["_observability_met"] = False
            reasons.append("observability-undeclared")
        else:
            f["_observability_required"] = req
            f["_observability_met"] = req <= run_level
            if req > run_level:
                reasons.append(f"observability-exceeds-run(req=L{req}>run=L{run_level})")
                stats["downgraded_obs"] += 1

        # FP-RISK — annotation. An unrecognized value still reads as high, so a
        # mis-cased "HIGH" is not quietly treated as low.
        fpr_raw = f.get("false_positive_risk")
        if fpr_raw is None:
            fpr = "low"
        elif isinstance(fpr_raw, str) and fpr_raw.lower() in FP_CAP:
            fpr = fpr_raw.lower()
        else:
            fpr = "high"
        f["_fp_risk"] = fpr

        # ZERO-WEIGHT — categorical. Advisory memos and the AI writing-style track
        # are reported in their own section and never form an integrity verdict.
        # Enforced by skill, pattern PREFIX and the deprecated-id set.
        zero_weight = _is_zero_weight(f)
        if zero_weight:
            capped = _cap(sev, "info")
            if capped != sev:
                reasons.append("zero-weight-cap")
                sev = capped

        # SURFACE — categorical label. Family-F presentation signals are a
        # "look closer" class, not an integrity claim.
        pid5 = f.get("pattern_id")
        pid5 = pid5.strip() if isinstance(pid5, str) else ""
        f["_surface_signal"] = bool(f.get("skill") in SURFACE_ONLY_SKILLS or pid5 in SURFACE_PATTERNS)

        # EXTERNAL-CHECK — annotation. The auditor itself marked this unsettled.
        f["_needs_external_check"] = bool(
            f.get("verdict_local") == "needs_external_check"
            or f.get("requires_external_check") is True)
        if f["_needs_external_check"]:
            reasons.append("auditor-marked-needs-external-check")

        f["_severity_original"] = original
        f["_severity_final"] = sev
        f["_verdict_weight"] = 0 if zero_weight else 1
        f["_adjudication"] = reasons
    return stats


def verdict_of(severities):
    if any(s == "critical" for s in severities):
        return "HARD_FLAGS"
    if any(s in ("major", "minor") for s in severities):
        return "SOFT_FLAGS"
    return "CLEAN_GIVEN_EVIDENCE"


def dimension_verdicts(findings):
    dims = {}
    for f in findings:
        if f.get("_verdict_weight", 1) != 1:   # zero-weight (AIS/ADV) never forms a dimension verdict
            continue
        dim = SKILL_TO_DIMENSION.get(f.get("skill"))
        if not dim:
            continue
        dims.setdefault(dim, "info")
        if SEV_ORDER[f["_severity_final"]] > SEV_ORDER[dims[dim]]:
            dims[dim] = f["_severity_final"]
    return {d: verdict_of([s]) for d, s in dims.items()}


def build_report(findings, args, stats, anchoring_verified, coverage=None,
                 refutation_cov=None, countercheck_cov=None):
    # The integrity verdict is computed from verdict-WEIGHT-1 findings ONLY. Zero-weight
    # findings (AIS style impressions + ADV memos) are reported but provably cannot move it.
    weighted = [f for f in findings if f.get("_verdict_weight", 1) == 1]
    finals = [f["_severity_final"] for f in weighted]
    counts = {k: sum(1 for s in finals if s == k) for k in ("critical", "major", "minor", "info")}
    counts["downgraded_for_observability"] = stats["downgraded_obs"]
    counts["unanchored_demoted"] = stats["unanchored"]
    counts["ai_style_impressions"] = sum(1 for f in findings if _is_ais(f))

    limitations = list(args.limitation or [])
    if args.observability_level < 2:
        limitations.append(
            "L%d run: code/result-level patterns (fake GT, self-normalization, "
            "phantom results, dead metrics) were NOT verifiable here. Any such finding "
            "in this report is a proposal the run could not confirm — its Observability "
            "column shows the level it needs." % args.observability_level
        )
    if args.observability_level == 0:
        limitations.append(
            "L0 (PDF-only): findings rest on extracted text spans; OCR/parse noise "
            "may affect low-confidence numeric claims."
        )
    if not anchoring_verified:
        limitations.append(
            "Anchoring NOT verified: the ledger has no usable claims, so no finding could "
            "be checked against a verbatim ledger span. Re-run /evidence-ledger."
        )
    # All proposed flags failed anchoring -> very likely an empty or STALE/mismatched ledger
    # (claim_ids are positional, so a findings.json from before a paper edit mis-anchors
    # wholesale). Surface this loudly: a CLEAN verdict here means "couldn't anchor", not "clean".
    # Scoped to verdict-bearing (weight-1) findings: an AIS/ADV finding failing anchoring is
    # not a stale-ledger signal.
    weighted_proposed = [f for f in weighted
                         if SEV_ORDER.get(f.get("_severity_original", "info"), 0) > 0]
    weighted_unanchored = [f for f in weighted_proposed if any(
        r in ("unanchored-demotion", "no-ledger-fail-closed") for r in f.get("_adjudication", []))]
    if weighted_proposed and len(weighted_unanchored) >= len(weighted_proposed):
        limitations.append(
            "All %d proposed above-info finding(s) failed anchoring and were demoted to info "
            "— likely an empty or stale/mismatched ledger (claim_ids are positional; a "
            "findings.json from before a paper edit mis-anchors wholesale). Rebuild the ledger "
            "with /evidence-ledger and re-audit before trusting this result." % len(weighted_proposed)
        )

    # Coverage gate: "no findings" must never be conflated with "the reviewer never ran".
    # A verdict-bearing dimension marked review_unavailable blocks the ACQUITTAL only —
    # findings already on the table still produce HARD/SOFT flags (flags can only add).
    provided = coverage is not None
    coverage = dict(coverage or {})
    if provided:
        # fail-closed: a PARTIAL (or empty) provided map must not read as a full sweep —
        # any verdict-bearing dimension absent from a provided map is treated as never-ran.
        for k in SKILL_TO_DIMENSION:
            coverage.setdefault(k, "review_unavailable")
    unavailable = sorted(k for k, v in coverage.items() if v == "review_unavailable")
    unavailable_vb = [k for k in unavailable if k in SKILL_TO_DIMENSION]
    overall = verdict_of(finals)
    if unavailable_vb:
        limitations.append(
            "COVERAGE INCOMPLETE: reviewer unavailable for verdict-bearing dimension(s) "
            "%s — this run is NOT a full sweep. A clean result here means 'nothing found "
            "in the dimensions that ran', never 'clean overall'." % ", ".join(unavailable_vb)
        )
        if overall == "CLEAN_GIVEN_EVIDENCE":
            overall = "REVIEW_UNAVAILABLE"
    for k in unavailable:
        if k not in SKILL_TO_DIMENSION:
            limitations.append(
                "Zero-weight track '%s' reviewer unavailable — its report section is "
                "missing; the integrity verdict is unaffected (zero verdict weight)." % k
            )

    refutation_cov = dict(refutation_cov or {"eligible": 0, "completed": 0,
                                             "unavailable": 0, "malformed": 0,
                                             "contested": 0})
    if countercheck_cov is None:
        countercheck_cov = refutation_cov.pop("countercheck", None)
    else:
        refutation_cov.pop("countercheck", None)
    if refutation_cov["eligible"] > refutation_cov["completed"]:
        limitations.append(
            "Critical-refutation pass incomplete: %d of %d eligible critical(s) never "
            "received a completed refutation attempt — the flags stand (flags fail toward "
            "caution), but the CONTESTED screen is missing for those findings."
            % (refutation_cov["eligible"] - refutation_cov["completed"],
               refutation_cov["eligible"]))

    return {
        "report_version": REPORT_VERSION,
        "taxonomy_version": args.taxonomy_version,
        "paper_id": args.paper_id,
        "observability_level": args.observability_level,
        "generated_at": args.generated_at or
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "overall_verdict": overall,
        "coverage": coverage,
        "critical_refutation_coverage": refutation_cov,
        "critical_countercheck": countercheck_cov or {
            "eligible": 0, "proved_compatible": 0, "informational": 0,
            "discrepancy_persists": 0, "unresolvable": 0, "basis_invalid": 0},
        "adjudicator": ADJUDICATOR_ID,
        "anchoring_verified": anchoring_verified,
        "dimension_verdicts": dimension_verdicts(findings),
        "findings": findings,
        "adversarial_memo": args.memo or "",
        "taxonomy_matches": _taxonomy_matches(findings),
        "counts": counts,
        "limitations": limitations,
        "human_review_required": True,
    }


def _taxonomy_matches(findings):
    by_pat = {}
    for f in findings:
        pid = f.get("pattern_id")
        if pid:
            by_pat.setdefault(pid, []).append(f.get("finding_id", "?"))
    return [{"pattern_id": k, "finding_ids": v} for k, v in sorted(by_pat.items())]


def _coverage_md(report):
    cov = report.get("coverage") or {}
    if not cov:
        return []
    icon = {"completed": "✅", "not_applicable": "➖", "review_unavailable": "⛔"}
    rows = [f"| `{k}` | {icon.get(v, '?')} {v} |" for k, v in sorted(cov.items())]
    return ["", "## Coverage", "", "| Skill | Status |", "|---|---|"] + rows


def render_md(report):
    v = report["overall_verdict"]
    badge = {"HARD_FLAGS": "🔴 HARD_FLAGS", "SOFT_FLAGS": "🟡 SOFT_FLAGS",
             "CLEAN_GIVEN_EVIDENCE": "🟢 CLEAN_GIVEN_EVIDENCE",
             "REVIEW_UNAVAILABLE": "⚪ REVIEW_UNAVAILABLE (incomplete sweep — not an acquittal)"}[v]
    lines = [
        f"# Integrity Forensics Report — {report['paper_id']}",
        "",
        f"**Verdict:** {badge}  ·  **Observability:** L{report['observability_level']}  "
        f"·  **Taxonomy:** v{report['taxonomy_version']}  ·  **Adjudicator:** {report['adjudicator']}",
        "",
        f"> This is decision SUPPORT for a human reviewer. It flags discrepancies to "
        f"investigate — it does **not** judge misconduct. `CLEAN_GIVEN_EVIDENCE` means "
        f"\"nothing checkable at L{report['observability_level']} is broken\", not \"the paper is honest\".",
        "",
        "> **How to read the table.** Every proposal an auditor made is listed, at the "
        "severity that auditor proposed. The verdict above applies a fixed rule to those "
        "proposals; it is not a ruling that they stand. The columns are what you weigh: "
        "`Anchored: NO` means the quoted span was not found in the paper (that proposal "
        "is already dropped to info); `Observability L2 ✗` means the auditor said it needs "
        "evidence this run did not have; `FP-risk: high` is the auditor's own estimate that "
        "it may be a false positive; `Surface` marks a presentation signal rather than an "
        "integrity claim; `Ext-check` means the auditor marked it unsettled itself.",
        "",
        "## Findings (evidence first)",
        "",
        "| ID | Dimension | Severity | Pattern | Where | Anchored | Observability | FP-risk | Surface | Ext-check | Contest |",
        "|----|-----------|----------|---------|-------|----------|---------------|---------|---------|-----------|---------|",
    ]
    # Everything the auditors proposed is shown. Demotion used to remove findings
    # from this table entirely, so a reader could not even disagree with it; the
    # columns now carry what the gates used to decide silently.
    shown = [f for f in report["findings"] if f.get("_verdict_weight", 1) == 1]
    for f in sorted(shown, key=lambda x: (-SEV_ORDER[x["_severity_final"]],
                                          -SEV_ORDER.get(x.get("_severity_original", "info"), 0))):
        loc = ""
        for ev in f.get("evidence", []) or []:
            l = ev.get("location") or {}
            fname = os.path.basename(l.get("file", "?")) if l.get("file") else "?"
            loc = f"{fname}:{l.get('section', l.get('line',''))}"
            break
        sev_cell = f["_severity_final"]
        if f["_severity_final"] != f.get("_severity_original"):
            sev_cell = f"{f['_severity_final']} (proposed {f['_severity_original']})"
        req = f.get("_observability_required")
        obs = "—" if req is None else (f"L{req} ✓" if f.get("_observability_met") else f"L{req} ✗ (run L{report['observability_level']})")
        lines.append(
            f"| {f.get('finding_id','?')} | {SKILL_TO_DIMENSION.get(f.get('skill'),'—')} "
            f"| {sev_cell} | {f.get('pattern_id','—')} | {loc or '—'} "
            f"| {'yes' if f.get('_anchored') else 'NO'} | {obs} "
            f"| {f.get('_fp_risk', f.get('false_positive_risk','—'))} "
            f"| {'yes' if f.get('_surface_signal') else '—'} "
            f"| {'yes' if f.get('_needs_external_check') else '—'} "
            f"| {'⚠️ CONTESTED' if f.get('_contested') else '—'} |"
        )
    if not shown:
        lines.append("| — | — | no findings proposed | — | — | — | — | — | — | — | — |")
    if any(f.get("_contested") for f in shown):
        lines += ["",
                  "> ⚠️ **CONTESTED** = a fresh adversarial refutation pass produced a "
                  "ledger-anchored counter-reading of this finding. Severity and verdict are "
                  "UNCHANGED — the refuter is same-family adversarial redundancy, not "
                  "independent verification, and no model output moves the verdict here. "
                  "Read both spans and decide."]

    lines += ["", "### Detail", ""]
    for f in sorted(shown, key=lambda x: (-SEV_ORDER[x["_severity_final"]],
                                          -SEV_ORDER.get(x.get("_severity_original", "info"), 0))):
        lines.append(f"**{f.get('finding_id','?')} — {f.get('title','')}** "
                     f"({f['_severity_final']})")
        lines.append("")
        lines.append(f"- {f.get('description','')}")
        if f.get("_contested"):
            ref = f.get("refutation") or {}
            lines.append(f"  - ⚠️ contested — refuter's reading: {ref.get('reason', '(no reason recorded)')}")
            for cev in (ref.get("counter_evidence") or [])[:2]:
                if (cev.get("span") or "").strip():
                    span_txt = (cev.get("span") or "")[:160]
                    lines.append(f"    - counter-anchor `{cev.get('claim_id','?')}`: {span_txt}")
        for ev in f.get("evidence", []) or []:
            if (ev.get("span") or "").strip():
                lines.append(f"  - evidence `{ev.get('claim_id','?')}`: "
                             f"“{ev['span'].strip()}”")
        if f.get("recommended_reviewer_action"):
            lines.append(f"  - reviewer action: {f['recommended_reviewer_action']}")
        if f.get("_adjudication"):
            lines.append(f"  - _adjudicator: {', '.join(f['_adjudication'])}_")
        lines.append("")

    adv = [f for f in report["findings"]
           if f.get("_verdict_weight", 1) == 0 and not _is_ais(f)]
    if adv:
        lines += [
            "## Advisory memos — NOT integrity findings · ZERO verdict weight",
            "",
            "> Prior-work overlap and adversarial-case material. Listed so nothing an "
            "auditor produced is invisible; these never form a verdict.",
            "",
            "| ID | Skill | Pattern | Where |",
            "|----|-------|---------|-------|",
        ]
        for f in adv:
            loc = ""
            for ev in f.get("evidence", []) or []:
                l = ev.get("location") or {}
                fname = os.path.basename(l.get("file", "?")) if l.get("file") else "?"
                loc = f"{fname}:{l.get('section', l.get('line',''))}"
                break
            lines.append(f"| {f.get('finding_id','?')} | {f.get('skill','—')} "
                         f"| {f.get('pattern_id','—')} | {loc or '—'} |")
        lines.append("")

    ais = [f for f in report["findings"] if _is_ais(f)]
    if ais:
        lines += [
            "## AI Writing-Style Impressions — NOT integrity findings · ZERO verdict weight",
            "",
            "> Transparent, itemized impressions of AI-generated **writing style**. These are "
            "**not** factual/integrity inconsistencies and carry **zero** weight on the verdict "
            "above — a paper can be `CLEAN_GIVEN_EVIDENCE` and still list many. No authorship "
            "probability is implied; this is reviewer-impression context, not a judgment.",
            "",
            "| ID | Signal | Where |",
            "|----|--------|-------|",
        ]
        for f in ais:
            loc = ""
            for ev in f.get("evidence", []) or []:
                l = ev.get("location") or {}
                fname = os.path.basename(l.get("file", "?")) if l.get("file") else "?"
                loc = f"{fname}:{l.get('section', l.get('line', ''))}"
                break
            lines.append(f"| {f.get('finding_id','?')} | {f.get('pattern_id','—')} | {loc or '—'} |")
        lines += ["", "### Impression detail", ""]
        for f in ais:
            lines.append(f"**{f.get('finding_id','?')} — {f.get('title','')}** "
                         f"(`{f.get('pattern_id','—')}` · impression, no verdict weight)")
            lines.append("")
            lines.append(f"- {f.get('description','')}")
            for ev in f.get("evidence", []) or []:
                if (ev.get("span") or "").strip():
                    lines.append(f"  - where `{ev.get('claim_id','?')}`: “{ev['span'].strip()}”")
            if f.get("fp_case"):
                lines.append(f"  - not-necessarily-AI: {f['fp_case']}")
            if f.get("recommended_reviewer_action"):
                lines.append(f"  - reviewer note: {f['recommended_reviewer_action']}")
            lines.append("")

    if report.get("adversarial_memo"):
        lines += ["## Adversarial memo (informational — no verdict weight)", "",
                  report["adversarial_memo"], ""]

    c = report["counts"]
    resolved = [f for f in report["findings"]
                if (f.get("_deterministic_countercheck") or {}).get("status") == "PROVED_COMPATIBLE"
                and f.get("_severity_final") == "info"]
    if resolved:
        lines += ["", "## Deterministically resolved criticals", "",
                  "_The following critical accusations were demoted to info by a "
                  "COMPUTATION (interval arithmetic over the displayed precision of "
                  "the very numbers they cite) proving the discrepancy cannot be "
                  "established. No model output took part in the demotion._", ""]
        for f in resolved:
            cc = f["_deterministic_countercheck"]
            lines.append(f"- **{f.get('finding_id','?')}** (`{f.get('pattern_id','—')}`) — "
                         f"resolver `{cc.get('resolver','?')}` v{cc.get('version','?')}: "
                         f"inputs {cc.get('inputs',{})}")
    lines += _coverage_md(report)
    lines += [
        "",
        "## Counts",
        "",
        f"- critical: {c['critical']}  ·  major: {c['major']}  ·  minor: {c['minor']}  "
        f"·  info: {c['info']}",
        f"- needing evidence this run lacked: {c['downgraded_for_observability']}  ·  "
        f"dropped as unanchored: {c.get('unanchored_demoted', 0)}",
        f"- AI writing-style impressions (zero verdict weight): {c.get('ai_style_impressions', 0)}",
        "",
        "## Limitations",
        "",
    ]
    for lim in report["limitations"]:
        lines.append(f"- {lim}")
    lines += ["", "_Human review required: always. This report does not issue a "
              "verdict on misconduct._"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic adjudicator for Anti-Autoresearch findings.")
    ap.add_argument("--findings", nargs="+", required=True, help="findings.json file(s)")
    ap.add_argument("--ledger", required=True, help="claims.json — REQUIRED. Every "
                    "above-info finding must quote a verbatim span of a real ledger claim; "
                    "without it nothing can be anchored and all findings fail closed to info.")
    ap.add_argument("--paper-id", required=True)
    ap.add_argument("--observability-level", type=int, required=True, choices=[0, 1, 2, 3])
    ap.add_argument("--taxonomy-version", default="0.5")
    ap.add_argument("--coverage", default="", help="coverage.json — per-skill run status "
                    "{skill: completed|not_applicable|review_unavailable}. A verdict-bearing "
                    "dimension marked review_unavailable BLOCKS the acquittal: the overall "
                    "verdict becomes REVIEW_UNAVAILABLE instead of CLEAN_GIVEN_EVIDENCE "
                    "(found flags still stand). Absent = legacy behavior.")
    ap.add_argument("--list-critical-candidates", action="store_true",
                    help="print the refutation-eligible criticals (post-gates) as JSON and exit "
                         "— the workflow's Step 3.5 uses this instead of re-deriving the rules")
    ap.add_argument("--memo", default="", help="adversarial memo text (informational)")
    ap.add_argument("--limitation", action="append", help="extra limitation line (repeatable)")
    ap.add_argument("--generated-at", default="", help="override timestamp (for reproducible eval)")
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--md", default="REPORT.md")
    args = ap.parse_args(argv)

    findings = load_findings(args.findings)

    coverage = None          # None = flag absent (legacy); {} = provided-but-empty (fail-closed)
    if args.coverage:
        with open(args.coverage, "r", encoding="utf-8") as fh:
            coverage = json.load(fh)
        bad = {k: v for k, v in (coverage or {}).items()
               if v not in ("completed", "not_applicable", "review_unavailable")}
        if bad:
            ap.error(f"invalid coverage status(es): {bad} — allowed: "
                     "completed | not_applicable | review_unavailable")
        known = set(SKILL_TO_DIMENSION) | set(ZERO_WEIGHT_SKILLS)
        unknown = sorted(k for k in (coverage or {}) if k not in known)
        if unknown:
            ap.error(f"unknown coverage skill key(s): {unknown} — a typo here would "
                     f"silently bypass the acquittal gate. Known keys: {sorted(known)}")

    with open(args.ledger, "r", encoding="utf-8") as fh:
        ledger = json.load(fh)
    ledger_map = {c.get("claim_id"): c.get("text_span", "")
                  for c in ledger.get("claims", []) if c.get("claim_id")}
    # parsed numeric values (value: {raw, normalized, unit}) — the ONLY numbers a
    # counter-check computation may consume (model-supplied numbers never reach it)
    ledger_values = {c.get("claim_id"): c.get("value")
                     for c in ledger.get("claims", [])
                     if c.get("claim_id") and isinstance(c.get("value"), dict)
                     and c["value"].get("normalized") is not None
                     and isinstance(c["value"].get("raw"), str)}

    # An empty ledger (no usable claims) can anchor nothing -> anchoring is NOT verified,
    # and every above-info finding silently fails closed. Report that honestly instead of
    # stamping a falsely-reassuring "anchoring_verified: true" on a CLEAN verdict.
    anchoring_verified = bool(ledger_map)
    stats = adjudicate(findings, args.observability_level, ledger_map or None)
    refutation_cov = apply_critical_scrutiny(findings, ledger_map or None, ledger_values)
    countercheck_cov = refutation_cov.pop("countercheck")

    if args.list_critical_candidates:
        # refutation-eligible criticals, AFTER every gate — the single source of truth
        # the workflow's Step 3.5 consumes (never re-derive these rules elsewhere)
        # re-entrant: a finding that already carries ANY refutation attempt
        # (completed / unavailable / malformed — each had its one retry) is done;
        # only never-attempted criticals are listed.
        cands = [{"source_file": f.get("_source_file", "?"),
                  "finding_id": f.get("finding_id", "?"),
                  "skill": f.get("skill", "?"),
                  "pattern_id": f.get("pattern_id", ""),
                  "title": f.get("title", "")}
                 for f in findings
                 if _is_llm_critical(f) and "refutation" not in f]
        print(json.dumps(cands, indent=2, ensure_ascii=False))
        return 0

    report = build_report(findings, args, stats, anchoring_verified=anchoring_verified,
                          coverage=coverage, refutation_cov=refutation_cov,
                          countercheck_cov=countercheck_cov)

    md = render_md(report)          # render FIRST — a render crash must not leave
    with open(args.out, "w", encoding="utf-8") as fh:   # a report.json without its REPORT.md
        json.dump(report, fh, indent=2, ensure_ascii=False)
    with open(args.md, "w", encoding="utf-8") as fh:
        fh.write(md)

    print(f"verdict={report['overall_verdict']} "
          f"crit={report['counts']['critical']} maj={report['counts']['major']} "
          f"min={report['counts']['minor']} -> {args.out}, {args.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
