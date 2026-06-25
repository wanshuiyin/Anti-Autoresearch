#!/usr/bin/env python3
"""
check_numeric_consistency.py — deterministic, arithmetic-only consistency checks.

This is the part of consistency forensics that needs NO language model: pure
arithmetic over the evidence ledger. It emits findings.json (finding.schema.json)
that the adjudicator consumes exactly like LLM-proposed findings — but these are
reproducible and form the backbone of the eval harness.

Checks (v0):
  HP-DELTA-ERROR   (major) — stated relative/absolute improvement contradicts the
                             arithmetic of its own two operands.
  HP-NUM-INFLATE   (minor) — a metric-bearing headline %-number in abstract/intro/
                             conclusion does not appear in any extracted table cell
                             (high FP risk; a signal to look, demoted by adjudicator).

LLM skills add the *semantic* consistency findings (method drift, ablation
attribution, wrong-context citations); those cannot be done by arithmetic.
"""
import argparse
import json
import re
import sys

# Tolerant of "from a 73.1% baseline to 78.0% accuracy, a 16.7% relative improvement"
DELTA_P1 = re.compile(
    r"from\s+[^\d.]{0,12}?(\d+(?:\.\d+)?)\s*%?[^.]{0,40}?\bto\s+[^\d.]{0,12}?(\d+(?:\.\d+)?)\s*%?"
    r"[^.]{0,80}?(\d+(?:\.\d+)?)\s*%\s*(relative\s+)?"
    r"(gain|improvement|increase|boost|reduction|drop)",
    re.IGNORECASE)
DELTA_P2 = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*(relative\s+)?(gain|improvement|increase|boost)"
    r"[^.]{0,80}?from\s+[^\d.]{0,12}?(\d+(?:\.\d+)?)\s*%?[^.]{0,40}?\bto\s+[^\d.]{0,12}?(\d+(?:\.\d+)?)",
    re.IGNORECASE)
TOL = 0.6  # percentage-point tolerance for rounding


def _norm(span):
    return span.replace("\\%", "%").replace("\\,", " ")


def _rel(a, b):
    return (b - a) / a * 100.0 if a else float("inf")


def check_delta(claims):
    findings, seen = [], set()
    n = 0
    for c in claims:
        raw = c.get("text_span", "")
        span = _norm(raw)
        loc = c.get("location", {})
        for rx, order in ((DELTA_P1, "ab_stated"), (DELTA_P2, "stated_ab")):
            for m in rx.finditer(span):
                if order == "ab_stated":
                    a, b, stated, rel_word, dir_word = (
                        m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
                else:
                    stated, rel_word, dir_word, a, b = (
                        m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
                key = (loc.get("file"), loc.get("line"), a, b, stated)
                if key in seen:
                    continue
                seen.add(key)
                a, b, stated = float(a), float(b), float(stated)
                rel, ab = _rel(a, b), b - a
                claims_relative = bool(rel_word)
                # a "reduction/drop/decrease" is reported as a positive magnitude on
                # a lower-better metric, where rel/ab are negative — compare |.|.
                decrease = bool(re.search(r"reduc|drop|decreas|lower|fewer", dir_word or "", re.I))
                rel_cmp = abs(rel) if decrease else rel
                ab_cmp = abs(ab) if decrease else ab
                ok = (abs(stated - rel_cmp) <= TOL) if claims_relative else (
                    abs(stated - rel_cmp) <= TOL or abs(stated - abs(ab_cmp)) <= TOL)
                if ok:
                    continue
                n += 1
                findings.append({
                    "finding_id": f"NUM{n:03d}",
                    "skill": "consistency-audit",
                    "pattern_id": "HP-DELTA-ERROR",
                    "title": "Stated improvement contradicts its operands",
                    "description": (
                        f"Text states a {stated:g}% {'relative ' if claims_relative else ''}"
                        f"change, but {a:g}->{b:g} is {rel:.1f}% relative "
                        f"({ab:+.1f} absolute points)."),
                    "severity": "major",
                    "observability_level_required": 0,
                    "evidence": [{
                        "claim_id": c.get("claim_id", "?"),
                        "span": raw,
                        "location": loc,
                        "artifact_hash": c.get("evidence_anchor", ""),
                    }],
                    "verdict_local": "fail",
                    "reviewer": {"deterministic": True},
                    "false_positive_risk": "low",
                    "recommended_reviewer_action": (
                        "Ask the authors to reconcile the stated delta with the "
                        "reported operands; verify relative-vs-absolute convention."),
                })
    return findings


def check_headline_in_tables(claims):
    table_vals = set()
    for c in claims:
        if c.get("type") == "table_cell":
            v = (c.get("value") or {}).get("normalized")
            if isinstance(v, (int, float)):
                table_vals.add(round(v, 1))
    if not table_vals:
        return []  # no tables extracted -> cannot run this check
    findings, n, seen = [], 0, set()
    for c in claims:
        if c.get("type") != "number":
            continue
        loc = c.get("location") or {}
        sec = loc.get("section", "") or ""
        val = c.get("value") or {}
        # only metric-bearing headline %-numbers (skip deltas like "6.7% improvement")
        if val.get("unit") != "%" or not val.get("metric"):
            continue
        if not isinstance(val.get("normalized"), (int, float)):
            continue
        if not any(k in sec for k in ("abstract", "intro", "conclusion")):
            continue
        if round(val["normalized"], 1) in table_vals:
            continue
        key = (sec, round(val["normalized"], 1))
        if key in seen:
            continue
        seen.add(key)
        n += 1
        findings.append({
            "finding_id": f"HL{n:03d}",
            "skill": "consistency-audit",
            "pattern_id": "HP-NUM-INFLATE",
            "title": "Headline number not found in any results table",
            "description": (
                f"The {sec} cites {val['normalized']:g}% {val['metric']} but no "
                f"extracted table cell reports that value; may be a different "
                f"setting, a rounding artifact, or an inflated headline."),
            "severity": "minor",
            "observability_level_required": 0,
            "evidence": [{
                "claim_id": c.get("claim_id", "?"),
                "span": c.get("text_span", ""),
                "location": loc,
                "artifact_hash": c.get("evidence_anchor", ""),
            }],
            "verdict_local": "warn",
            "reviewer": {"deterministic": True},
            "false_positive_risk": "high",
            "recommended_reviewer_action": (
                "Locate the headline number's source table/row; confirm the "
                "setting it refers to."),
        })
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic numeric consistency checks.")
    ap.add_argument("--ledger", required=True, help="claims.json from build_claim_ledger.py")
    ap.add_argument("--out", default="consistency-audit.deterministic.findings.json")
    args = ap.parse_args(argv)

    with open(args.ledger, "r", encoding="utf-8") as fh:
        ledger = json.load(fh)
    claims = ledger.get("claims", [])

    findings = check_delta(claims) + check_headline_in_tables(claims)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2, ensure_ascii=False)
    print(f"deterministic findings: {len(findings)} "
          f"({sum(1 for f in findings if f['pattern_id']=='HP-DELTA-ERROR')} delta, "
          f"{sum(1 for f in findings if f['pattern_id']=='HP-NUM-INFLATE')} headline) "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
