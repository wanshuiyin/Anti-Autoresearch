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
    f = _f(skill="consistency-audit", pattern_id="HP-AI-FLAVOR")  # critical by default
    assert _final([f]) == ["minor"]
    assert "surface-only-cap" in f["_adjudication"]


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
