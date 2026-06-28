#!/usr/bin/env python3
"""
Unit tests for the deterministic adjudicator gates — these lock in the anti-slop
guarantee (a finding can only raise the verdict if it is ledger-anchored, declares
its observability need, survives the FP cap, and is not memo-only).

Run: python3 tests/test_adjudicator.py   (also pytest-compatible)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import adjudicate_findings as A  # noqa: E402

LEDGER = {"C001": "FooNet reaches 78.0% accuracy on BarBench, a strong result."}


def _f(**kw):
    base = {"finding_id": "F1", "skill": "consistency-audit", "severity": "critical",
            "observability_level_required": 0,
            "evidence": [{"claim_id": "C001", "span": "FooNet reaches 78.0% accuracy"}],
            "false_positive_risk": "low"}
    base.update(kw)
    return base


def _final(findings, run_level=2, ledger=LEDGER):
    A.adjudicate(findings, run_level, ledger)
    return [f["_severity_final"] for f in findings]


def test_anchored_critical_survives():
    assert _final([_f()]) == ["critical"]
    assert A.verdict_of(["critical"]) == "HARD_FLAGS"


def test_unanchored_demoted_even_minor():
    # minor with a span that is NOT in the ledger -> info (closes the minor hole)
    f = _f(severity="minor", evidence=[{"claim_id": "C999", "span": "made up text"}])
    assert _final([f]) == ["info"]
    assert "unanchored-demotion" in f["_adjudication"]


def test_no_evidence_demoted():
    assert _final([_f(severity="major", evidence=[])]) == ["info"]


def test_missing_observability_req_fails_closed():
    f = _f()
    del f["observability_level_required"]
    assert _final([f]) == ["info"]
    assert "undeclared-observability" in f["_adjudication"]


def test_observability_above_run_demoted():
    # an L2 code-level critical, run at L0 -> info (cannot shout fraud from a PDF)
    f = _f(observability_level_required=2)
    assert _final([f], run_level=0) == ["info"]


def test_fp_high_caps_to_minor():
    assert _final([_f(false_positive_risk="high")]) == ["minor"]


def test_memo_only_skill_capped_to_info():
    f = _f(skill="adversarial-case-builder")
    assert _final([f]) == ["info"]


def test_surface_only_skill_capped_to_minor():
    # presentation/AI-flavor signals cap at minor -> at most SOFT_FLAGS, never HARD
    f = _f(skill="presentation-signals")  # critical by default
    assert _final([f]) == ["minor"]
    assert "surface-only-cap" in f["_adjudication"]
    assert A.verdict_of(["minor"]) == "SOFT_FLAGS"


def test_surface_pattern_capped_even_under_other_skill():
    # an F-pattern smuggled in under a non-surface skill is STILL capped at minor
    f = _f(skill="consistency-audit", pattern_id="HP-THIN-FLOAT")  # critical by default
    assert _final([f]) == ["minor"]
    assert "surface-only-cap" in f["_adjudication"]


def test_surface_pattern_strip_bypass_rejected():
    # a dirty pattern_id with a trailing space must STILL hit the surface cap (-> minor)
    f = _f(skill="consistency-audit", pattern_id="HP-THIN-FLOAT ")  # critical by default
    assert _final([f]) == ["minor"]
    assert "surface-only-cap" in f["_adjudication"]


def test_advisory_pattern_capped_even_under_other_skill():
    # an ADV-* advisory pattern smuggled in under a verdict-bearing skill is STILL info
    f = _f(skill="consistency-audit", pattern_id="ADV-TRIVIAL-COMBINATION")  # critical by default
    assert _final([f]) == ["info"]
    assert "zero-weight-cap" in f["_adjudication"]


def test_ais_skill_zero_weight():
    # an AIS impression, even proposed critical + anchored, is forced to info, weight 0
    f = _f(skill="ai-style-impressions", pattern_id="AIS-DEFENSIVE-HEDGE")
    assert _final([f]) == ["info"]
    assert f["_verdict_weight"] == 0
    assert "zero-weight-cap" in f["_adjudication"]


def test_ais_prefix_zero_weight_under_other_skill():
    # an AIS-* pattern smuggled under a verdict-bearing skill is STILL zero-weight info
    f = _f(skill="consistency-audit", pattern_id="AIS-LLM-PHRASE-TICS")
    assert _final([f]) == ["info"]
    assert f["_verdict_weight"] == 0


def test_deprecated_style_pattern_zero_weight():
    # an OLD HP-* style id migrated to AIS is forced zero-weight: a stale findings.json
    # can no longer push HP-AI-FLAVOR to SOFT_FLAGS
    f = _f(skill="presentation-signals", pattern_id="HP-AI-FLAVOR")
    assert _final([f]) == ["info"]
    assert f["_verdict_weight"] == 0


def test_zero_weight_never_moves_overall_verdict():
    # THE invariant: a clean paper with an AIS finding proposed critical stays CLEAN, and the
    # AIS impression is still reported (counts.ai_style_impressions == 1, critical == 0).
    import types
    ais = _f(skill="ai-style-impressions", pattern_id="AIS-DEFENSIVE-HEDGE")  # critical, anchored
    stats = A.adjudicate([ais], 2, LEDGER)
    args = types.SimpleNamespace(observability_level=2, limitation=None,
                                 taxonomy_version="0.5", paper_id="t", generated_at="x", memo="")
    rep = A.build_report([ais], args, stats, anchoring_verified=True)
    assert rep["overall_verdict"] == "CLEAN_GIVEN_EVIDENCE"
    assert rep["counts"]["ai_style_impressions"] == 1
    assert rep["counts"]["critical"] == 0


def test_zero_weight_not_in_dimension_verdicts():
    # a zero-weight finding (deprecated style id under a verdict-bearing skill) must NOT
    # create an integrity dimension verdict
    import types
    f = _f(skill="presentation-signals", pattern_id="HP-AI-FLAVOR")  # critical, anchored, zero-weight
    stats = A.adjudicate([f], 2, LEDGER)
    args = types.SimpleNamespace(observability_level=2, limitation=None,
                                 taxonomy_version="0.5", paper_id="t", generated_at="x", memo="")
    rep = A.build_report([f], args, stats, anchoring_verified=True)
    assert rep["dimension_verdicts"] == {}, rep["dimension_verdicts"]
    assert rep["overall_verdict"] == "CLEAN_GIVEN_EVIDENCE"


def test_integrity_and_ais_coexist():
    # a real integrity critical + an AIS critical -> HARD from integrity; AIS stays zero-weight
    import types
    integ = _f(skill="consistency-audit", pattern_id="HP-NUM-INFLATE")  # critical, anchored
    ais = _f(skill="ai-style-impressions", pattern_id="AIS-DEFENSIVE-HEDGE")
    stats = A.adjudicate([integ, ais], 2, LEDGER)
    args = types.SimpleNamespace(observability_level=2, limitation=None,
                                 taxonomy_version="0.5", paper_id="t", generated_at="x", memo="")
    rep = A.build_report([integ, ais], args, stats, anchoring_verified=True)
    assert rep["overall_verdict"] == "HARD_FLAGS"
    assert integ["_verdict_weight"] == 1 and ais["_verdict_weight"] == 0
    assert rep["counts"]["ai_style_impressions"] == 1


def test_needs_external_check_capped_to_info():
    # a finding the auditor itself marks unsettled cannot raise the verdict
    assert _final([_f(verdict_local="needs_external_check")]) == ["info"]
    assert _final([_f(requires_external_check=True)]) == ["info"]


def test_short_span_not_anchored():
    # a 1-char / punctuation-only span is a substring of almost any claim -> must NOT anchor
    for bad in ("a", ".", "  ", "%"):
        f = _f(evidence=[{"claim_id": "C001", "span": bad}])
        assert _final([f]) == ["info"], bad


def test_fp_garbled_token_fails_closed():
    # a present-but-unrecognized FP token (mis-cased / typo / non-str) -> treated high -> minor
    assert _final([_f(false_positive_risk="HIGH")]) == ["minor"]
    assert _final([_f(false_positive_risk="bogus")]) == ["minor"]
    assert _final([_f(false_positive_risk=5)]) == ["minor"]


def test_fp_medium_caps_to_major():
    assert _final([_f(false_positive_risk="medium")]) == ["major"]


def test_observability_out_of_range_fails_closed():
    assert _final([_f(observability_level_required=7)]) == ["info"]
    assert _final([_f(observability_level_required=-1)]) == ["info"]


def test_malformed_findings_do_not_crash():
    # non-str pattern_id / non-str span / non-str severity must not raise (and must not anchor)
    assert _final([_f(pattern_id=123)]) == ["critical"]   # int pid: no crash, still anchors via good span
    assert _final([_f(evidence=[{"claim_id": "C001", "span": 123}])]) == ["info"]  # non-str span -> not anchored
    assert _final([_f(severity=None)]) == ["info"]        # non-str severity -> treated as info


def test_stale_ledger_adds_loud_limitation():
    # every above-info finding fails anchoring (cites an absent claim_id) -> CLEAN, but LOUDLY caveated
    import types
    f = _f(evidence=[{"claim_id": "C999", "span": "totally fabricated finding text here"}])
    stats = A.adjudicate([f], 2, {"C001": "real claim"})
    args = types.SimpleNamespace(observability_level=2, limitation=None,
                                 taxonomy_version="0.3", paper_id="t", generated_at="x", memo="")
    rep = A.build_report([f], args, stats, anchoring_verified=True)
    assert rep["overall_verdict"] == "CLEAN_GIVEN_EVIDENCE"
    assert any("failed anchoring" in lim for lim in rep["limitations"])


def test_verdict_levels():
    assert A.verdict_of(["info"]) == "CLEAN_GIVEN_EVIDENCE"
    assert A.verdict_of(["minor"]) == "SOFT_FLAGS"
    assert A.verdict_of(["major"]) == "SOFT_FLAGS"
    assert A.verdict_of(["critical", "info"]) == "HARD_FLAGS"


def test_no_ledger_fails_closed():
    # without a ledger nothing can be anchored -> everything demoted to info
    f = _f()
    assert _final([f], ledger=None) == ["info"]
    assert "no-ledger-fail-closed" in f["_adjudication"]


def test_span_padding_bypass_rejected():
    # real claim text + appended hallucination must NOT anchor (only span in base)
    f = _f(evidence=[{"claim_id": "C001",
                      "span": LEDGER["C001"] + " AND FABRICATED EXTRA TEXT"}])
    assert _final([f]) == ["info"]


def test_json_boolean_observability_rejected():
    # observability_level_required: true  (JSON bool, ==1 in python) must be rejected
    f = _f(observability_level_required=True)
    assert _final([f], run_level=1) == ["info"]
    assert "undeclared-observability" in f["_adjudication"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
