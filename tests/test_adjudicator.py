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


def test_verdict_levels():
    assert A.verdict_of(["info"]) == "CLEAN_GIVEN_EVIDENCE"
    assert A.verdict_of(["minor"]) == "SOFT_FLAGS"
    assert A.verdict_of(["major"]) == "SOFT_FLAGS"
    assert A.verdict_of(["critical", "info"]) == "HARD_FLAGS"


def test_no_ledger_falls_back_to_span_presence_with_warning_field():
    # without a ledger, a non-empty span passes the (weaker) presence check
    assert _final([_f()], ledger=None) == ["critical"]


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
