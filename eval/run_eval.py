#!/usr/bin/env python3
"""
run_eval.py — the calibration / regression harness.

Per codex's design review: "without an eval harness this project gets dismissed."
It proves the DETERMINISTIC core end-to-end with zero language model in the loop:

  clean fixture        -> ledger -> deterministic checks -> adjudicator
  + synthetic defects  -> (injected by corrupt.py) -> must be caught

For each fixture it asserts:
  - every `required_patterns` entry is present above info-severity   (no false negatives)
  - `forbidden_above_info` fixtures raise nothing above info          (no false positives)
  - the adjudicated verdict matches `expected_verdict` / `min_verdict`

Exit code 0 = all pass (CI gate). Non-zero = a regression. Reports a precision/
recall-style summary so taxonomy/extractor changes are measured, not vibes.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS = os.path.join(ROOT, "tools")
RUN_DIR = os.path.join(HERE, ".eval_run")
CLEAN = os.path.join(HERE, "fixtures", "clean", "sample_paper.tex")
CORR_DIR = os.path.join(HERE, "fixtures", "synthetic_corruptions")
EXPECT = os.path.join(HERE, "expected_findings")
FIXED_TS = "2026-01-01T00:00:00Z"
VRANK = {"CLEAN_GIVEN_EVIDENCE": 0, "SOFT_FLAGS": 1, "HARD_FLAGS": 2}

sys.path.insert(0, HERE)
import corrupt  # noqa: E402


def run(cmd):
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout); print(r.stderr, file=sys.stderr)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return r.stdout.strip()


def prepare_fixtures():
    os.makedirs(RUN_DIR, exist_ok=True)
    os.makedirs(CORR_DIR, exist_ok=True)
    fixtures = [("clean", CLEAN)]
    with open(CLEAN, encoding="utf-8") as fh:
        clean_text = fh.read()
    for name in sorted(corrupt.CORRUPTIONS):
        out = os.path.join(CORR_DIR, f"{name}.tex")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(corrupt.apply_corruption(clean_text, name))
        fixtures.append((name, out))
    return fixtures


def audit(name, tex):
    ledger = os.path.join(RUN_DIR, f"{name}.claims.json")
    findings = os.path.join(RUN_DIR, f"{name}.findings.json")
    report = os.path.join(RUN_DIR, f"{name}.report.json")
    md = os.path.join(RUN_DIR, f"{name}.REPORT.md")
    run([os.path.join(TOOLS, "build_claim_ledger.py"), "--paper-id", name,
         "--latex", tex, "--observability-level", "1", "--out", ledger])
    run([os.path.join(TOOLS, "check_numeric_consistency.py"), "--ledger", ledger, "--out", findings])
    run([os.path.join(TOOLS, "adjudicate_findings.py"), "--findings", findings,
         "--ledger", ledger, "--paper-id", name, "--observability-level", "1",
         "--generated-at", FIXED_TS, "--out", report, "--md", md])
    with open(report, encoding="utf-8") as fh:
        return json.load(fh)


def evaluate(name, report):
    exp_path = os.path.join(EXPECT, f"{name}.json")
    with open(exp_path, encoding="utf-8") as fh:
        exp = json.load(fh)
    above_info = [f for f in report["findings"] if f.get("_severity_final") != "info"]
    found = {f.get("pattern_id") for f in above_info if f.get("pattern_id")}
    required = set(exp.get("required_patterns", []))

    fn = sorted(required - found)
    extra = sorted(found - required)  # precision gate: unexpected patterns are FPs
    fp_clean = exp.get("forbidden_above_info") and len(above_info) > 0
    tp = sorted(required & found)

    verdict = report["overall_verdict"]
    verr = None
    if "expected_verdict" in exp and verdict != exp["expected_verdict"]:
        verr = f"verdict {verdict} != expected {exp['expected_verdict']}"
    if "min_verdict" in exp and VRANK[verdict] < VRANK[exp["min_verdict"]]:
        verr = f"verdict {verdict} < min {exp['min_verdict']}"

    # every above-info finding must be span-anchored (the core invariant)
    unanchored = [f["finding_id"] for f in above_info
                  if not any((e.get("span") or "").strip() for e in f.get("evidence", []))]

    ok = not fn and not extra and not fp_clean and not verr and not unanchored
    return {
        "name": name, "ok": ok, "verdict": verdict,
        "tp": tp, "fn": fn, "extra": extra, "fp_clean": fp_clean, "verr": verr,
        "unanchored": unanchored, "n_above_info": len(above_info),
    }


def main():
    fixtures = prepare_fixtures()
    results = [evaluate(name, audit(name, tex)) for name, tex in fixtures]

    print("\n=== Anti-Autoresearch eval (deterministic core) ===\n")
    print(f"{'fixture':<20}{'verdict':<22}{'result':<8}{'detail'}")
    print("-" * 78)
    TP = FN = 0
    all_ok = True
    for r in results:
        TP += len(r["tp"]); FN += len(r["fn"])
        detail = []
        if r["tp"]:
            detail.append("caught=" + ",".join(r["tp"]))
        if r["fn"]:
            detail.append("MISSED=" + ",".join(r["fn"]))
        if r["extra"]:
            detail.append("UNEXPECTED=" + ",".join(r["extra"]))
        if r["fp_clean"]:
            detail.append(f"FALSE-POSITIVE x{r['n_above_info']}")
        if r["verr"]:
            detail.append(r["verr"])
        if r["unanchored"]:
            detail.append("UNANCHORED=" + ",".join(r["unanchored"]))
        print(f"{r['name']:<20}{r['verdict']:<22}{'PASS' if r['ok'] else 'FAIL':<8}"
              f"{'; '.join(detail) or 'clean'}")
        all_ok = all_ok and r["ok"]

    recall = TP / (TP + FN) if (TP + FN) else 1.0
    print("-" * 78)
    print(f"\ninjected-defect recall: {recall:.0%} ({TP}/{TP + FN})  ·  "
          f"clean false-positives: {'none' if all(not r['fp_clean'] for r in results) else 'SOME'}")
    print(f"\noverall: {'PASS ✅' if all_ok else 'FAIL ❌'}\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
