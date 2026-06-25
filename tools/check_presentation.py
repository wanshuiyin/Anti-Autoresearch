#!/usr/bin/env python3
"""
check_presentation.py — deterministic surface-signal checks.

These are the *presentation*-level signals (the cluster-A "AI-flavor / low-effort"
family) that can be computed without a model. v0 ships the one that is objective and
eval-testable: duplicate/near-identical tables (HP-DUP-TABLE).

IMPORTANT: surface signals are weak and high-false-positive. Every finding here is
emitted under skill "presentation-signals", which the adjudicator caps at `minor`
(SURFACE_ONLY_SKILLS) — they can contribute at most SOFT_FLAGS, never HARD_FLAGS,
and they are NOT an AI-generation verdict. See references/hack-pattern-taxonomy.md
section F. The richer surface signals (AI-flavor prose, LLM-looking figures,
page-padding, jargon-stuffing) are semantic and live in skills/presentation-signals.
"""
import argparse
import json
import re
import sys

MIN_CELLS = 2  # tables with fewer numeric cells than this are ignored (too collision-prone)


def table_signatures(claims):
    """Map table section label -> (ordered tuple of cell values, a representative span)."""
    tables = {}
    for c in claims:
        if c.get("type") != "table_cell":
            continue
        sec = (c.get("location") or {}).get("section", "")
        if not re.match(r"table:\d+", sec or ""):
            continue
        v = (c.get("value") or {}).get("normalized")
        if not isinstance(v, (int, float)):
            continue
        tables.setdefault(sec, {"vals": [], "claim_id": c.get("claim_id"),
                                "span": c.get("text_span", ""),
                                "anchor": c.get("evidence_anchor", ""),
                                "loc": c.get("location", {})})
        tables[sec]["vals"].append(round(v, 4))
    return tables


def check_duplicate_tables(claims):
    tables = table_signatures(claims)
    findings, n, seen_pairs = [], 0, set()
    keys = sorted(tables)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = tables[keys[i]], tables[keys[j]]
            if len(a["vals"]) < MIN_CELLS or len(b["vals"]) < MIN_CELLS:
                continue
            if a["vals"] != b["vals"]:
                continue
            pair = (keys[i], keys[j])
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            n += 1
            findings.append({
                "finding_id": f"PRES{n:03d}",
                "skill": "presentation-signals",
                "pattern_id": "HP-DUP-TABLE",
                "title": "Two tables have identical numeric content",
                "description": (
                    f"{keys[i]} and {keys[j]} contain the same ordered cell values "
                    f"({a['vals']}); may be padding or an un-updated copy-paste."),
                "severity": "minor",
                "observability_level_required": 0,
                "evidence": [
                    {"claim_id": a["claim_id"], "span": a["span"], "location": a["loc"],
                     "artifact_hash": a["anchor"]},
                    {"claim_id": b["claim_id"], "span": b["span"], "location": b["loc"],
                     "artifact_hash": b["anchor"]},
                ],
                "verdict_local": "warn",
                "reviewer": {"deterministic": True},
                "false_positive_risk": "high",
                "recommended_reviewer_action": (
                    "Check whether the two tables are meant to differ; if identical, "
                    "ask why both are present."),
            })
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic surface-signal checks.")
    ap.add_argument("--ledger", required=True, help="claims.json from build_claim_ledger.py")
    ap.add_argument("--out", default="presentation-signals.deterministic.findings.json")
    args = ap.parse_args(argv)

    with open(args.ledger, "r", encoding="utf-8") as fh:
        ledger = json.load(fh)
    findings = check_duplicate_tables(ledger.get("claims", []))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2, ensure_ascii=False)
    print(f"presentation findings: {len(findings)} "
          f"({sum(1 for f in findings if f['pattern_id']=='HP-DUP-TABLE')} dup-table) "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
