#!/usr/bin/env python3
"""
adjudicate_findings.py — the deterministic adjudicator.

The structural defense against "LLM slop grading LLM slop": the language-model
auditors PROPOSE findings (each anchored to an evidence-ledger span); this script
DECIDES the verdict by fixed rules. No model is in the final decision, so the
verdict is reproducible: same findings + same observability level -> same verdict.

Gates applied to every finding, in order (each may demote severity and is logged):
  1. SPAN gate         — critical/major with no non-empty evidence span -> info.
  2. OBSERVABILITY gate — observability_level_required > run level       -> info.
  3. FP-RISK gate      — false_positive_risk high -> cap at minor; medium -> cap at major.
  4. MEMO gate         — adversarial-case-builder is memo-only           -> cap at info.

Verdict rule (after gating):
  any critical                 -> HARD_FLAGS
  else any major/minor         -> SOFT_FLAGS
  else                         -> CLEAN_GIVEN_EVIDENCE   (NOT "the paper is honest")

Pure standard library. See references/{reviewer-independence,observability-levels,
integrity-forensics-contract}.md.
"""
import argparse
import datetime
import json
import os
import sys

REPORT_VERSION = "0.1"
ADJUDICATOR_ID = "deterministic-rules-v0"

SEV_ORDER = {"info": 0, "minor": 1, "major": 2, "critical": 3}
SEV_NAME = {v: k for k, v in SEV_ORDER.items()}

SKILL_TO_DIMENSION = {
    "consistency-audit": "consistency",
    "experiment-forensics": "experiment",
    "baseline-comparison-audit": "baseline",
    "citation-forensics": "citation",
}
MEMO_ONLY_SKILLS = {"adversarial-case-builder"}
FP_CAP = {"high": "minor", "medium": "major", "low": "critical"}


def _cap(sev, cap):
    """Return the lower of sev and cap (by severity order)."""
    return sev if SEV_ORDER[sev] <= SEV_ORDER[cap] else cap


def _has_span(finding):
    for ev in finding.get("evidence", []) or []:
        if (ev.get("span") or "").strip():
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
            it.setdefault("_source_file", p)
            findings.append(it)
    return findings


def adjudicate(findings, run_level):
    downgraded_obs = 0
    for f in findings:
        original = f.get("severity", "info")
        if original not in SEV_ORDER:
            original = "info"
        sev = original
        reasons = []

        # 1. SPAN gate
        if SEV_ORDER[sev] >= SEV_ORDER["major"] and not _has_span(f):
            sev = "info"
            reasons.append("no-span-demotion")

        # 2. OBSERVABILITY gate
        req = f.get("observability_level_required", 0) or 0
        if req > run_level and SEV_ORDER[sev] > SEV_ORDER["info"]:
            sev = "info"
            reasons.append(f"observability-demotion(req=L{req}>run=L{run_level})")
            downgraded_obs += 1

        # 3. FP-RISK gate
        cap = FP_CAP.get(f.get("false_positive_risk", "low"), "critical")
        capped = _cap(sev, cap)
        if capped != sev:
            reasons.append(f"fp-cap({f.get('false_positive_risk')})")
            sev = capped

        # 4. MEMO gate
        if f.get("skill") in MEMO_ONLY_SKILLS:
            capped = _cap(sev, "info")
            if capped != sev:
                reasons.append("memo-only-skill")
                sev = capped

        f["_severity_original"] = original
        f["_severity_final"] = sev
        f["_adjudication"] = reasons
    return downgraded_obs


def verdict_of(severities):
    if any(s == "critical" for s in severities):
        return "HARD_FLAGS"
    if any(s in ("major", "minor") for s in severities):
        return "SOFT_FLAGS"
    return "CLEAN_GIVEN_EVIDENCE"


def dimension_verdicts(findings):
    dims = {}
    for f in findings:
        dim = SKILL_TO_DIMENSION.get(f.get("skill"))
        if not dim:
            continue
        dims.setdefault(dim, "info")
        if SEV_ORDER[f["_severity_final"]] > SEV_ORDER[dims[dim]]:
            dims[dim] = f["_severity_final"]
    return {d: verdict_of([s]) for d, s in dims.items()}


def build_report(findings, args, downgraded_obs):
    finals = [f["_severity_final"] for f in findings]
    counts = {k: sum(1 for s in finals if s == k) for k in ("critical", "major", "minor", "info")}
    counts["downgraded_for_observability"] = downgraded_obs

    limitations = list(args.limitation or [])
    if args.observability_level < 2:
        limitations.append(
            "L%d run: code/result-level patterns (fake GT, self-normalization, "
            "phantom results, dead metrics) were NOT verifiable and appear only as "
            "info-level 'could-not-check' signals." % args.observability_level
        )
    if args.observability_level == 0:
        limitations.append(
            "L0 (PDF-only): findings rest on extracted text spans; OCR/parse noise "
            "may affect low-confidence numeric claims."
        )

    return {
        "report_version": REPORT_VERSION,
        "taxonomy_version": args.taxonomy_version,
        "paper_id": args.paper_id,
        "observability_level": args.observability_level,
        "generated_at": args.generated_at or datetime.datetime.utcnow().isoformat() + "Z",
        "overall_verdict": verdict_of(finals),
        "adjudicator": ADJUDICATOR_ID,
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


def render_md(report):
    v = report["overall_verdict"]
    badge = {"HARD_FLAGS": "🔴 HARD_FLAGS", "SOFT_FLAGS": "🟡 SOFT_FLAGS",
             "CLEAN_GIVEN_EVIDENCE": "🟢 CLEAN_GIVEN_EVIDENCE"}[v]
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
        "## Findings (evidence first)",
        "",
        "| ID | Dimension | Severity | Pattern | Where | FP-risk |",
        "|----|-----------|----------|---------|-------|---------|",
    ]
    shown = [f for f in report["findings"] if f["_severity_final"] != "info"]
    for f in sorted(shown, key=lambda x: -SEV_ORDER[x["_severity_final"]]):
        loc = ""
        for ev in f.get("evidence", []) or []:
            l = ev.get("location") or {}
            fname = os.path.basename(l.get("file", "?")) if l.get("file") else "?"
            loc = f"{fname}:{l.get('section', l.get('line',''))}"
            break
        lines.append(
            f"| {f.get('finding_id','?')} | {SKILL_TO_DIMENSION.get(f.get('skill'),'—')} "
            f"| {f['_severity_final']} | {f.get('pattern_id','—')} | {loc or '—'} "
            f"| {f.get('false_positive_risk','—')} |"
        )
    if not shown:
        lines.append("| — | — | none above info | — | — | — |")

    lines += ["", "### Detail", ""]
    for f in sorted(shown, key=lambda x: -SEV_ORDER[x["_severity_final"]]):
        lines.append(f"**{f.get('finding_id','?')} — {f.get('title','')}** "
                     f"({f['_severity_final']})")
        lines.append("")
        lines.append(f"- {f.get('description','')}")
        for ev in f.get("evidence", []) or []:
            if (ev.get("span") or "").strip():
                lines.append(f"  - evidence `{ev.get('claim_id','?')}`: "
                             f"“{ev['span'].strip()}”")
        if f.get("recommended_reviewer_action"):
            lines.append(f"  - reviewer action: {f['recommended_reviewer_action']}")
        if f.get("_adjudication"):
            lines.append(f"  - _adjudicator: {', '.join(f['_adjudication'])}_")
        lines.append("")

    if report.get("adversarial_memo"):
        lines += ["## Adversarial memo (informational — no verdict weight)", "",
                  report["adversarial_memo"], ""]

    c = report["counts"]
    lines += [
        "## Counts",
        "",
        f"- critical: {c['critical']}  ·  major: {c['major']}  ·  minor: {c['minor']}  "
        f"·  info: {c['info']}",
        f"- demoted for observability: {c['downgraded_for_observability']}",
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
    ap.add_argument("--paper-id", required=True)
    ap.add_argument("--observability-level", type=int, required=True, choices=[0, 1, 2, 3])
    ap.add_argument("--taxonomy-version", default="0.1")
    ap.add_argument("--memo", default="", help="adversarial memo text (informational)")
    ap.add_argument("--limitation", action="append", help="extra limitation line (repeatable)")
    ap.add_argument("--generated-at", default="", help="override timestamp (for reproducible eval)")
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--md", default="REPORT.md")
    args = ap.parse_args(argv)

    findings = load_findings(args.findings)
    downgraded_obs = adjudicate(findings, args.observability_level)
    report = build_report(findings, args, downgraded_obs)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    with open(args.md, "w", encoding="utf-8") as fh:
        fh.write(render_md(report))

    print(f"verdict={report['overall_verdict']} "
          f"crit={report['counts']['critical']} maj={report['counts']['major']} "
          f"min={report['counts']['minor']} -> {args.out}, {args.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
