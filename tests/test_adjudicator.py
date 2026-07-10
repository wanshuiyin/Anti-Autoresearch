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


# ---- coverage gate (review_unavailable must never masquerade as CLEAN) ----

class _Args:
    def __init__(self):
        self.limitation = []
        self.observability_level = 2
        self.taxonomy_version = "0.5"
        self.paper_id = "t"
        self.generated_at = "2026-01-01T00:00:00Z"
        self.memo = ""


def _report(findings, coverage):
    A.adjudicate(findings, 2, LEDGER)
    return A.build_report(findings, _Args(), {"downgraded_obs": 0, "unanchored": 0},
                          anchoring_verified=True, coverage=coverage)


def test_unavailable_verdict_bearing_dim_blocks_acquittal():
    r = _report([], {"consistency-audit": "review_unavailable"})
    assert r["overall_verdict"] == "REVIEW_UNAVAILABLE"
    assert any("COVERAGE INCOMPLETE" in l for l in r["limitations"])


def test_unavailable_dim_does_not_erase_found_flags():
    f = _f()  # anchored critical
    r = _report([f], {"experiment-forensics": "review_unavailable"})
    assert r["overall_verdict"] == "HARD_FLAGS"          # flags stand
    assert any("COVERAGE INCOMPLETE" in l for l in r["limitations"])


def test_zero_weight_track_unavailable_keeps_clean():
    cov = {k: "completed" for k in A.SKILL_TO_DIMENSION}
    cov["ai-style-impressions"] = "review_unavailable"
    r = _report([], cov)
    assert r["overall_verdict"] == "CLEAN_GIVEN_EVIDENCE"
    assert any("Zero-weight track" in l for l in r["limitations"])


def test_completed_and_not_applicable_do_not_gate():
    # a FULL map (fail-closed fills missing verdict-bearing keys as unavailable,
    # so a clean acquittal needs every dimension accounted for)
    cov = {"consistency-audit": "completed", "experiment-forensics": "completed",
           "baseline-comparison-audit": "not_applicable", "citation-forensics": "completed",
           "presentation-signals": "completed", "proof-derivation-forensics": "completed",
           "eval-design-forensics": "completed"}
    r = _report([], cov)
    assert r["overall_verdict"] == "CLEAN_GIVEN_EVIDENCE"
    assert r["coverage"]["baseline-comparison-audit"] == "not_applicable"


def test_cli_unknown_coverage_key_rejected():
    # a typo'd skill key must never silently bypass the acquittal gate
    import json, tempfile, os
    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "claims.json")
        json.dump({"claims": [{"claim_id": "C001", "text_span": "x"}]}, open(led, "w"))
        cov = os.path.join(d, "cov.json")
        json.dump({"consistency_audit": "review_unavailable"}, open(cov, "w"))  # typo: underscore
        fnd = os.path.join(d, "f.json")
        json.dump([], open(fnd, "w"))
        try:
            A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
                    "--observability-level", "2", "--coverage", cov,
                    "--out", os.path.join(d, "r.json"), "--md", os.path.join(d, "r.md")])
            assert False, "unknown coverage key must be rejected"
        except SystemExit as e:
            assert e.code != 0


def test_cli_review_unavailable_renders_md_and_json():
    import json, tempfile, os
    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "claims.json")
        json.dump({"claims": [{"claim_id": "C001", "text_span": "x"}]}, open(led, "w"))
        cov = os.path.join(d, "cov.json")
        json.dump({"consistency-audit": "review_unavailable"}, open(cov, "w"))
        fnd = os.path.join(d, "f.json")
        json.dump([], open(fnd, "w"))
        out, md = os.path.join(d, "r.json"), os.path.join(d, "r.md")
        rc = A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
                     "--observability-level", "2", "--coverage", cov,
                     "--out", out, "--md", md])
        assert rc == 0
        r = json.load(open(out))
        assert r["overall_verdict"] == "REVIEW_UNAVAILABLE"
        assert r["coverage"]["consistency-audit"] == "review_unavailable"
        m = open(md).read()
        assert "REVIEW_UNAVAILABLE" in m and "## Coverage" in m   # badge + coverage table render


def test_partial_coverage_map_fails_closed():
    # a provided map missing verdict-bearing keys must read as never-ran, not full sweep
    r = _report([], {"consistency-audit": "completed"})
    assert r["overall_verdict"] == "REVIEW_UNAVAILABLE"
    assert r["coverage"]["experiment-forensics"] == "review_unavailable"


def test_empty_provided_coverage_map_fails_closed():
    r = _report([], {})       # provided-but-empty != absent
    assert r["overall_verdict"] == "REVIEW_UNAVAILABLE"


def test_absent_coverage_stays_legacy():
    r = _report([], None)
    assert r["overall_verdict"] == "CLEAN_GIVEN_EVIDENCE"
    assert r["coverage"] == {}


# ---- critical scrutiny: alternative-explanation gate + CONTESTED marking ----

def _crit(**kw):
    f = _f()   # anchored critical, weight-1
    f["alternative_explanation_checked"] = "ruled out rounding and unit conventions"
    f.update(kw)
    return f


def _scrutinize(findings, cov_expect=None):
    A.adjudicate(findings, 2, LEDGER)
    rc = A.apply_critical_scrutiny(findings, LEDGER)
    if cov_expect:
        for k, v in cov_expect.items():
            assert rc[k] == v, (k, rc)
    return rc


def test_critical_without_alternative_explanation_demotes_to_major():
    f = _f()   # no alternative_explanation_checked
    _scrutinize([f])
    assert f["_severity_final"] == "major"
    assert "alternative-explanation-not-declared" in f["_adjudication"]


def test_critical_with_alternative_explanation_stands():
    f = _crit()
    _scrutinize([f], {"eligible": 1, "unavailable": 1})
    assert f["_severity_final"] == "critical"


def test_deterministic_critical_exempt_from_gate():
    f = _f(reviewer={"deterministic": True})
    _scrutinize([f], {"eligible": 0})
    assert f["_severity_final"] == "critical"   # computed, not argued — no gate


def test_anchored_refutation_marks_contested_but_never_demotes():
    f = _crit(refutation={"attempt_status": "completed", "refuted": True,
                          "reason": "same value under rounding",
                          "counter_evidence": [{"claim_id": "C001",
                                                "span": "FooNet reaches 78.0% accuracy"}]})
    _scrutinize([f], {"eligible": 1, "completed": 1, "contested": 1})
    assert f["_severity_final"] == "critical"          # severity untouched
    assert f.get("_contested") is True
    assert A.verdict_of([f["_severity_final"]]) == "HARD_FLAGS"   # verdict untouched


def test_unanchored_refutation_is_not_contested():
    f = _crit(refutation={"attempt_status": "completed", "refuted": True,
                          "reason": "just an opinion",
                          "counter_evidence": [{"claim_id": "C001", "span": "made up counter"}]})
    _scrutinize([f], {"contested": 0, "completed": 1})
    assert not f.get("_contested")
    assert "unanchored-refutation-claim" in f["_adjudication"]


def test_refutation_unavailable_counts_and_flag_stands():
    f = _crit(refutation={"attempt_status": "unavailable"})
    _scrutinize([f], {"eligible": 1, "unavailable": 1, "completed": 0})
    assert f["_severity_final"] == "critical"


def test_report_carries_refutation_coverage_and_limitation():
    f = _crit()   # eligible but no refutation attempt
    A.adjudicate([f], 2, LEDGER)
    rc = A.apply_critical_scrutiny([f], LEDGER)
    r = A.build_report([f], _Args(), {"downgraded_obs": 0, "unanchored": 0},
                       anchoring_verified=True, coverage=None, refutation_cov=rc)
    assert r["critical_refutation_coverage"]["eligible"] == 1
    assert any("Critical-refutation pass incomplete" in l for l in r["limitations"])


def test_contested_renders_in_md():
    f = _crit(refutation={"attempt_status": "completed", "refuted": True,
                          "reason": "rounding convention",
                          "counter_evidence": [{"claim_id": "C001",
                                                "span": "FooNet reaches 78.0% accuracy"}]})
    A.adjudicate([f], 2, LEDGER)
    rc = A.apply_critical_scrutiny([f], LEDGER)
    r = A.build_report([f], _Args(), {"downgraded_obs": 0, "unanchored": 0},
                       anchoring_verified=True, coverage=None, refutation_cov=rc)
    md = A.render_md(r)
    assert "CONTESTED" in md and "not\nindependent verification".replace("\n", " ") in md.replace("\n", " ")


def test_cli_list_critical_candidates():
    import json, tempfile, os
    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "claims.json")
        json.dump({"claims": [{"claim_id": "C001",
                               "text_span": "FooNet reaches 78.0% accuracy on BarBench, a strong result."}]},
                  open(led, "w"))
        fnd = os.path.join(d, "f.json")
        json.dump([_crit()], open(fnd, "w"))
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
                         "--observability-level", "2", "--list-critical-candidates"])
        assert rc == 0
        cands = json.loads(buf.getvalue())
        assert len(cands) == 1 and cands[0]["finding_id"] == "F1"


# ---- round-2 review hardening: gaming/reset/malformed/attach-tool ----

def test_deterministic_string_false_does_not_exempt():
    # reviewer provenance is model-influenced — only the boolean True exempts
    f = _f(reviewer={"deterministic": "false"})   # no alternative_explanation_checked
    _scrutinize([f])
    assert f["_severity_final"] == "major"


def test_gamed_alternative_explanation_rejected():
    for v in (True, 1, {"x": 1}, "x", "   ok   "):
        f = _f(alternative_explanation_checked=v)
        _scrutinize([f])
        assert f["_severity_final"] == "major", repr(v)


def test_preset_contested_is_reset_each_round():
    f = _crit()
    f["_contested"] = True          # smuggled in / stale from a prior round
    _scrutinize([f])
    assert not f.get("_contested")  # no refutation this round -> no marker


def test_hollow_completed_counts_as_malformed():
    f = _crit(refutation={"attempt_status": "completed"})   # no refuted bool
    _scrutinize([f], {"malformed": 1, "completed": 0})
    f2 = _crit(refutation={"attempt_status": "bogus"})
    _scrutinize([f2], {"malformed": 1, "completed": 0})


def test_attach_refutation_tool_roundtrip():
    import json, os, subprocess, sys, tempfile
    tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools",
                        "attach_refutation.py")
    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "claims.json")
        json.dump({"claims": [{"claim_id": "C001",
                               "text_span": "FooNet reaches 78.0% accuracy on BarBench, a strong result."}]},
                  open(led, "w"))
        fnd = os.path.join(d, "f.json")
        json.dump([_crit()], open(fnd, "w"))
        env = dict(os.environ, ARIS_RESOLVED_MODEL="gpt-5.6-sol",
                   ARIS_RESOLVED_REASONING="xhigh")
        ce = json.dumps([{"claim_id": "C001", "span": "FooNet reaches 78.0% accuracy"},
                         {"claim_id": "C001", "span": "fabricated counter"}])
        r = subprocess.run([sys.executable, tool, "--findings-file", fnd,
                            "--finding-id", "F1", "--ledger", led,
                            "--status", "completed", "--refuted", "true",
                            "--reason", "rounding", "--counter-evidence", ce],
                           capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
        out = json.load(open(fnd))[0]
        assert out["refutation"]["refuted"] is True
        assert len(out["refutation"]["counter_evidence"]) == 1   # fabricated one dropped
        assert out["severity"] == "critical"                     # finding untouched
        # second attempt refused without --force-overwrite
        r2 = subprocess.run([sys.executable, tool, "--findings-file", fnd,
                             "--finding-id", "F1", "--ledger", led,
                             "--status", "unavailable"],
                            capture_output=True, text=True, env=env)
        assert r2.returncode != 0
        # unset resolved pair -> loud failure
        env2 = {k: v for k, v in env.items() if not k.startswith("ARIS_RESOLVED")}
        r3 = subprocess.run([sys.executable, tool, "--findings-file", fnd,
                             "--finding-id", "F1", "--ledger", led,
                             "--status", "unavailable", "--force-overwrite"],
                            capture_output=True, text=True, env=env2)
        assert r3.returncode != 0 and "ARIS_RESOLVED" in r3.stderr


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
