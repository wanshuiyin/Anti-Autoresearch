#!/usr/bin/env python3
"""
Tests for report.json self-binding (issue #17): coverage_provenance and
audited_content_fingerprint. Both are purely ADDITIVE — never gate the verdict.

Invariants under test:
- audited_content_fingerprint changes when the CONTENT of a present pdf/latex/bib
  artifact changes, stays STABLE when an unrelated file (e.g. report.json itself,
  or a repo/results-only artifact) changes, and is None when no --manifest was
  given or the manifest names zero present content artifacts.
- coverage_provenance is {} when coverage is absent/empty or the ledger has no
  source_files; otherwise every key in `coverage` gets a provenance entry, and
  every entry is the SAME whole-ledger hash (the honest limitation: no
  per-dimension claim subsetting exists today — see the function's docstring).
- Neither field ever appears in SEV_ORDER/verdict computation — a full CLI run
  with a HARD_FLAGS-worthy finding still returns HARD_FLAGS regardless of what
  either field contains.

Run: python3 tests/test_report_provenance.py   (also pytest-compatible)
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import adjudicate_findings as A  # noqa: E402
import build_manifest as M       # noqa: E402

LEDGER_WITH_SOURCES = {
    "claims": [{"claim_id": "C001", "text_span": "x"}],
    "source_files": [{"path": "main.tex", "sha256": "a" * 64, "kind": "latex"}],
}


# ---- pure functions: ledger_state_sha256 / coverage_provenance_of ----

def test_ledger_state_sha256_none_without_sources():
    assert A.ledger_state_sha256({"claims": []}) is None
    assert A.ledger_state_sha256({"claims": [], "source_files": []}) is None


def test_ledger_state_sha256_stable_and_order_independent():
    a = {"source_files": [{"path": "b.tex", "sha256": "2" * 64, "kind": "latex"},
                          {"path": "a.tex", "sha256": "1" * 64, "kind": "latex"}]}
    b = {"source_files": list(reversed(a["source_files"]))}   # same set, different order
    assert A.ledger_state_sha256(a) == A.ledger_state_sha256(b)


def test_ledger_state_sha256_changes_with_content():
    a = {"source_files": [{"path": "main.tex", "sha256": "1" * 64, "kind": "latex"}]}
    b = {"source_files": [{"path": "main.tex", "sha256": "2" * 64, "kind": "latex"}]}
    assert A.ledger_state_sha256(a) != A.ledger_state_sha256(b)


def test_coverage_provenance_empty_without_coverage_or_sources():
    assert A.coverage_provenance_of(None, LEDGER_WITH_SOURCES) == {}
    assert A.coverage_provenance_of({}, LEDGER_WITH_SOURCES) == {}
    assert A.coverage_provenance_of({"consistency-audit": "completed"}, {"claims": []}) == {}


def test_coverage_provenance_only_binds_completed_entries():
    # not_applicable (never consulted the ledger) and review_unavailable (never
    # ran) must NOT get a provenance hash — only what actually ran + read it
    cov = {"consistency-audit": "completed", "citation-forensics": "not_applicable",
           "baseline-comparison-audit": "review_unavailable"}
    prov = A.coverage_provenance_of(cov, LEDGER_WITH_SOURCES)
    assert set(prov) == {"consistency-audit"}
    state = A.ledger_state_sha256(LEDGER_WITH_SOURCES)
    assert prov["consistency-audit"] == state   # honest limitation: no per-dimension subset


def test_coverage_provenance_key_set_stable_across_fail_closed_normalization():
    # build_report()'s fail-closed fill only ever ADDS review_unavailable keys
    # for missing verdict-bearing skills — it never adds/changes a "completed"
    # entry, so the "completed" key set (and hence coverage_provenance's keys)
    # must be identical whether this is called before or after that fill.
    raw = {"consistency-audit": "completed"}
    normalized = dict(raw)
    for k in A.SKILL_TO_DIMENSION:
        normalized.setdefault(k, "review_unavailable")
    assert set(A.coverage_provenance_of(raw, LEDGER_WITH_SOURCES)) == \
           set(A.coverage_provenance_of(normalized, LEDGER_WITH_SOURCES)) == \
           {"consistency-audit"}


def test_ledger_state_sha256_changes_when_claims_change_but_sources_dont():
    # a re-run of build_claim_ledger.py that re-derives DIFFERENT claims from
    # byte-identical source files must be a different ledger state — hashing
    # source_files alone would miss this
    sources = [{"path": "main.tex", "sha256": "a" * 64, "kind": "latex"}]
    a = {"source_files": sources, "claims": [{"claim_id": "C001", "text_span": "old",
                                              "evidence_anchor": "a" * 64}]}
    b = {"source_files": sources, "claims": [{"claim_id": "C001", "text_span": "new",
                                              "evidence_anchor": "a" * 64}]}
    assert A.ledger_state_sha256(a) != A.ledger_state_sha256(b)


# ---- audited_content_fingerprint_of (pure, over an artifact_manifest.json shape) ----

def test_content_fingerprint_none_without_manifest_or_content_artifacts():
    assert A.audited_content_fingerprint_of(None) is None
    assert A.audited_content_fingerprint_of({"artifacts": []}) is None
    # repo/results artifacts carry no sha256 and must never fingerprint as "content"
    assert A.audited_content_fingerprint_of(
        {"artifacts": [{"kind": "repo", "present": True}]}) is None
    # present:false content artifacts don't count either
    assert A.audited_content_fingerprint_of(
        {"artifacts": [{"kind": "pdf", "path": "p.pdf", "sha256": "a" * 64, "present": False}]}
    ) is None


def test_content_fingerprint_stable_across_kind_order_but_changes_with_sha():
    m1 = {"artifacts": [{"kind": "pdf", "path": "p.pdf", "sha256": "1" * 64, "present": True},
                        {"kind": "latex", "path": "m.tex", "sha256": "2" * 64, "present": True}]}
    m2 = {"artifacts": list(reversed(m1["artifacts"]))}
    assert A.audited_content_fingerprint_of(m1) == A.audited_content_fingerprint_of(m2)
    m3 = json.loads(json.dumps(m1))
    m3["artifacts"][0]["sha256"] = "9" * 64
    assert A.audited_content_fingerprint_of(m1) != A.audited_content_fingerprint_of(m3)


def test_content_fingerprint_ignores_non_content_kinds():
    base = {"artifacts": [{"kind": "pdf", "path": "p.pdf", "sha256": "1" * 64, "present": True}]}
    with_repo = json.loads(json.dumps(base))
    with_repo["artifacts"].append({"kind": "repo", "present": True, "path": "code"})
    assert A.audited_content_fingerprint_of(base) == A.audited_content_fingerprint_of(with_repo)


# ---- end-to-end: real build_manifest.py output, real adjudicate_findings.py CLI ----

def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def test_e2e_fingerprint_changes_with_paper_content_stable_across_unrelated_edits():
    with tempfile.TemporaryDirectory() as d:
        tex = os.path.join(d, "main.tex")
        open(tex, "w").write("\\emph{16.7\\%}")
        led, fnd, cov = (os.path.join(d, n) for n in ("claims.json", "f.json", "cov.json"))
        _write_json(led, {"claims": [{"claim_id": "C001", "text_span": "x"}], "source_files": []})
        _write_json(fnd, [])
        _write_json(cov, {})
        man = os.path.join(d, "artifact_manifest.json")
        M.main(["--paper-id", "t", "--dir", d, "--out", man])

        out, md = os.path.join(d, "r.json"), os.path.join(d, "r.md")
        A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
               "--observability-level", "1", "--manifest", man, "--out", out, "--md", md])
        fp1 = json.load(open(out))["audited_content_fingerprint"]
        assert fp1 is not None and len(fp1) == 64

        # unrelated edit (an extraneous file the manifest never scans) -> stable
        open(os.path.join(d, "notes.txt"), "w").write("scratch")
        M.main(["--paper-id", "t", "--dir", d, "--out", man])
        A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
               "--observability-level", "1", "--manifest", man, "--out", out, "--md", md])
        assert json.load(open(out))["audited_content_fingerprint"] == fp1

        # content edit -> changes
        open(tex, "w").write("\\emph{18.9\\%}")
        M.main(["--paper-id", "t", "--dir", d, "--out", man])
        A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
               "--observability-level", "1", "--manifest", man, "--out", out, "--md", md])
        fp2 = json.load(open(out))["audited_content_fingerprint"]
        assert fp2 != fp1

        m = open(md).read()
        assert "Audited content:" in m   # render_md surfaces it


def test_e2e_absent_manifest_yields_null_fingerprint_and_empty_provenance():
    with tempfile.TemporaryDirectory() as d:
        led, fnd = os.path.join(d, "claims.json"), os.path.join(d, "f.json")
        _write_json(led, {"claims": [{"claim_id": "C001", "text_span": "x"}]})
        _write_json(fnd, [])
        out, md = os.path.join(d, "r.json"), os.path.join(d, "r.md")
        A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
               "--observability-level", "1", "--out", out, "--md", md])
        r = json.load(open(out))
        assert r["audited_content_fingerprint"] is None
        assert r["coverage_provenance"] == {}
        assert "Audited content:" not in open(md).read()


def test_e2e_malformed_manifest_rejected():
    with tempfile.TemporaryDirectory() as d:
        led, fnd = os.path.join(d, "claims.json"), os.path.join(d, "f.json")
        _write_json(led, {"claims": [{"claim_id": "C001", "text_span": "x"}]})
        _write_json(fnd, [])
        man = os.path.join(d, "bad_manifest.json")
        _write_json(man, {"not": "a manifest"})
        try:
            A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
                   "--observability-level", "1", "--manifest", man,
                   "--out", os.path.join(d, "r.json"), "--md", os.path.join(d, "r.md")])
            assert False, "malformed manifest must be rejected"
        except SystemExit as e:
            assert e.code != 0


def _adjudicate_variants(d, findings, coverage, ledger, use_manifest, use_coverage,
                         observability_level=2):
    led, fnd = os.path.join(d, "claims.json"), os.path.join(d, "f.json")
    _write_json(led, ledger)
    _write_json(fnd, findings)
    argv = ["--findings", fnd, "--ledger", led, "--paper-id", "t",
            "--observability-level", str(observability_level)]
    if use_coverage:
        cov = os.path.join(d, "cov.json")
        _write_json(cov, coverage or {})
        argv += ["--coverage", cov]
    if use_manifest:
        man = os.path.join(d, "artifact_manifest.json")
        tex = os.path.join(d, "main.tex")
        open(tex, "w").write("x")
        M.main(["--paper-id", "t", "--dir", d, "--out", man])
        argv += ["--manifest", man]
    out, md = os.path.join(d, "r.json"), os.path.join(d, "r.md")
    A.main(argv + ["--out", out, "--md", md])
    return json.load(open(out))


_CRITICAL_LEDGER = {"claims": [{"claim_id": "C001", "text_span": "FooNet reaches 78%."}],
                    "source_files": [{"path": "main.tex", "sha256": "a" * 64, "kind": "latex"}]}
_CRITICAL_FINDING = {"finding_id": "F1", "skill": "consistency-audit", "severity": "critical",
                     "observability_level_required": 0,
                     "evidence": [{"claim_id": "C001", "span": "FooNet reaches 78%"}],
                     "false_positive_risk": "low",
                     "alternative_explanation_checked": "no benign reading fits the anchored span"}
_VERDICT_SHAPE = ("overall_verdict", "counts", "dimension_verdicts", "limitations", "coverage")


def test_e2e_new_fields_are_differentially_inert_across_verdict_classes():
    # for each verdict class, running WITH vs WITHOUT --manifest/--coverage must
    # produce byte-identical verdict/counts/dimension_verdicts/limitations/coverage
    # — a test that only checks "still HARD_FLAGS" could pass even if the new
    # fields' presence unconditionally forced a verdict; this compares both runs.
    full_completed = {k: "completed" for k in A.SKILL_TO_DIMENSION}
    cases = [
        ("HARD_FLAGS", [_CRITICAL_FINDING], full_completed),
        ("SOFT_FLAGS", [dict(_CRITICAL_FINDING, severity="minor")], full_completed),
        ("CLEAN_GIVEN_EVIDENCE", [], full_completed),   # a PARTIAL map fails closed to REVIEW_UNAVAILABLE
        ("REVIEW_UNAVAILABLE", [], {"consistency-audit": "review_unavailable"}),
    ]
    for expect, findings, cov in cases:
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            bare = _adjudicate_variants(d1, findings, cov, _CRITICAL_LEDGER,
                                        use_manifest=False, use_coverage=True)
            rich = _adjudicate_variants(d2, findings, cov, _CRITICAL_LEDGER,
                                        use_manifest=True, use_coverage=True)
            assert bare["overall_verdict"] == expect, expect
            for key in _VERDICT_SHAPE:
                assert bare[key] == rich[key], f"{expect}: {key} differs with --manifest present"
            assert bare["coverage_provenance"] == rich["coverage_provenance"]
            assert rich["audited_content_fingerprint"] is not None
            assert bare["audited_content_fingerprint"] is None


def test_e2e_manifest_paper_id_mismatch_rejected():
    with tempfile.TemporaryDirectory() as d:
        led, fnd = os.path.join(d, "claims.json"), os.path.join(d, "f.json")
        _write_json(led, {"claims": [{"claim_id": "C001", "text_span": "x"}]})
        _write_json(fnd, [])
        man = os.path.join(d, "artifact_manifest.json")
        _write_json(man, {"paper_id": "other-paper", "artifacts": []})
        try:
            A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
                   "--observability-level", "1", "--manifest", man,
                   "--out", os.path.join(d, "r.json"), "--md", os.path.join(d, "r.md")])
            assert False, "mismatched manifest paper_id must be rejected"
        except SystemExit as e:
            assert e.code != 0


def test_e2e_manifest_bad_artifact_shape_rejected():
    with tempfile.TemporaryDirectory() as d:
        led, fnd = os.path.join(d, "claims.json"), os.path.join(d, "f.json")
        _write_json(led, {"claims": [{"claim_id": "C001", "text_span": "x"}]})
        _write_json(fnd, [])
        for bad_artifacts in (
            [{"kind": "pdf", "path": "p.pdf", "sha256": "not-a-real-sha", "present": True}],
            [{"kind": "quantum-flux", "present": True}],
            ["not-even-an-object"],
        ):
            man = os.path.join(d, "man.json")
            _write_json(man, {"paper_id": "t", "artifacts": bad_artifacts})
            try:
                A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
                       "--observability-level", "1", "--manifest", man,
                       "--out", os.path.join(d, "r.json"), "--md", os.path.join(d, "r.md")])
                assert False, f"bad artifact must be rejected: {bad_artifacts}"
            except SystemExit as e:
                assert e.code != 0


def test_e2e_malformed_manifest_does_not_block_list_critical_candidates():
    # manifest validation happens AFTER the --list-critical-candidates early
    # return — that path never consumes --manifest, so a broken one must not
    # block it (even though no current caller combines the two flags)
    with tempfile.TemporaryDirectory() as d:
        led, fnd = os.path.join(d, "claims.json"), os.path.join(d, "f.json")
        _write_json(led, {"claims": [{"claim_id": "C001", "text_span": "x"}]})
        _write_json(fnd, [])
        man = os.path.join(d, "man.json")
        _write_json(man, {"not": "a manifest"})
        rc = A.main(["--findings", fnd, "--ledger", led, "--paper-id", "t",
                    "--observability-level", "1", "--manifest", man,
                    "--list-critical-candidates"])
        assert rc == 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok {fn.__name__}")
    print(f"{len(fns)} passed")
