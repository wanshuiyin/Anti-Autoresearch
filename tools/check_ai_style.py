#!/usr/bin/env python3
"""
check_ai_style.py — deterministic arm of the AI writing-style impression track (AIS).

The AIS track is the repo's ONLY non-integrity output: transparent, itemized impressions of
AI-generated *writing style*. They are emitted under skill "ai-style-impressions" and the
adjudicator gives every AIS finding ZERO verdict weight (forced to info, excluded from the
verdict) — a paper can be `CLEAN_GIVEN_EVIDENCE` and still list many. We surface them because
reviewers demonstrably react to them, but they are NOT integrity findings and imply NO
authorship probability. We are not an opaque AI-text classifier.

Most AIS signals are semantic (the `ai-style-impressions` skill's reviewer pass). This tool
ships the ONE that is objectively computable: the defensive-hedge density screen
(`AIS-DEFENSIVE-HEDGE`). It fires only on a genuine pattern — never on one scoping sentence —
and flags the recurrence of the hedge SHAPE, never who wrote it.
"""
import argparse
import json
import re
import sys

# --- AIS-DEFENSIVE-HEDGE ------------------------------------------------------------
# A conservative DENSITY screen for defensive "we do not claim … / not X but rather Y"
# writing. NOT a low-FP exact match: one scoping sentence is legitimate (a Limitations
# section SHOULD hedge), so this fires only on a real PATTERN. Keep these strict templates a
# SUBSET of build_claim_ledger.HEDGE_CUES (that recall-net is what gets pure-prose hedges into
# the ledger as `scope` claims so this screen has anchored spans to cite).
DEFENSIVE_HEDGE_PATTERNS = (
    r"\bwe do not claim\b",
    r"\bwe make no claim\b",
    r"\bwe are not (?:claiming|proposing|arguing|suggesting)\b",
    r"\bwe do not (?:aim|seek|intend|attempt|propose|argue|wish) to\b",
    r"\bthis (?:does|did|should) not (?:mean|imply|suggest)\b",
    r"\bthis paper (?:does not|is not meant to|is not intended to) (?:claim|argue|prove|show|establish)\b",
    r"\bour (?:goal|aim|purpose|intention|objective) is not\b[^.;:]{0,60}\bbut\b",
    # "not X but rather Y" ONLY in an author/paper-stance context — a bare not-but-rather
    # ("not convex but rather piecewise smooth") is a normal technical contrast, not a hedge.
    r"\b(?:we|this (?:paper|work|study))\b[^.;:]{0,40}\bnot\b[^.;:]{1,40}\bbut rather\b",
    r"本文(?:并)?不(?:声称|主张|是要证明|旨在)",
    r"并不声称",
    r"并不主张",
    r"这并不意味着",
    r"目的不是[^。;:]{0,40}而是",
)
# Hedges in these sections are EXPECTED and legitimate; never counted toward the screen.
HEDGE_EXCLUDED_SECTION = re.compile(
    r"limitation|related[\s_-]*work|ethic|broader[\s_-]*impact|acknowledg", re.IGNORECASE)
HEDGE_MIN_SENTENCES = 4   # distinct hedge sentences required to fire (conservative)
HEDGE_MIN_SECTIONS = 2    # ...spread across at least this many non-excluded sections
HEDGE_MIN_RATIO = 0.25    # ...AND hedges must be >=this fraction of all scope sentences, so a
                          # long honest paper with a few scattered caveats stays below threshold


def check_defensive_hedge(claims, start=0):
    """Deterministic AIS density screen for defensive-hedge writing (AIS-DEFENSIVE-HEDGE).
    Scans ledger `scope` claims for STRONG defensive templates and fires ONE impression only
    when the paper shows a genuine pattern: >=HEDGE_MIN_SENTENCES distinct hedge sentences
    across >=HEDGE_MIN_SECTIONS non-excluded sections AND >=HEDGE_MIN_RATIO of all scope
    sentences. Conservative by design; ZERO verdict weight (the adjudicator forces it to info);
    NEVER an authorship verdict — it flags the recurrence of the hedge SHAPE only."""
    rx = [re.compile(p, re.IGNORECASE) for p in DEFENSIVE_HEDGE_PATTERNS]
    seen_scope, scope_total = set(), 0     # distinct non-excluded `scope` claims (the denominator)
    seen_hit, hits = set(), []
    for c in claims:
        # Only `scope`-language claims (precision): a hedge that also carries a number/citation
        # still gets its OWN scope claim from build_claim_ledger.HEDGE_CUES, so nothing is lost.
        if c.get("type") != "scope":
            continue
        span_text = c.get("text_span")
        if not isinstance(span_text, str) or not span_text:
            continue
        loc = c.get("location", {})
        sec = loc.get("section", "") or ""
        if HEDGE_EXCLUDED_SECTION.search(sec):     # a hedge in Limitations/Related-Work is expected
            continue
        norm = " ".join(span_text.split())
        key = (sec, norm)                          # dedup by (section, normalized sentence)
        if key not in seen_scope:
            seen_scope.add(key)
            scope_total += 1                       # denominator: every distinct scope sentence
        if not any(r.search(span_text) for r in rx):
            continue
        if key in seen_hit:
            continue
        seen_hit.add(key)
        hits.append({"claim_id": c.get("claim_id"), "span": norm[:300], "location": loc,
                     "anchor": c.get("evidence_anchor", ""), "section": sec})
    sections = {h["section"] for h in hits}
    # Fire ONLY on a genuine pattern. NB: PDF-text ledgers label every claim section "unknown",
    # so the >=2-section gate makes this effectively LaTeX-decided — conservative by design.
    if (len(hits) < HEDGE_MIN_SENTENCES or len(sections) < HEDGE_MIN_SECTIONS
            or len(hits) < HEDGE_MIN_RATIO * scope_total):
        return []
    evidence = [{"claim_id": h["claim_id"], "span": h["span"], "location": h["location"],
                 "artifact_hash": h["anchor"]} for h in hits[:3]]
    sec_list = ", ".join(sorted(s for s in sections if s)) or "multiple sections"
    return [{
        "finding_id": f"AIS{start + 1:03d}",
        "skill": "ai-style-impressions",
        "pattern_id": "AIS-DEFENSIVE-HEDGE",
        "title": "Pervasive defensive-hedge writing across multiple sections",
        "description": (
            f"{len(hits)} distinct defensive-hedge constructions (e.g. \"we do not claim …\", "
            f"\"not X but rather Y\") across {len(sections)} non-excluded sections ({sec_list}). "
            f"The text repeatedly defends against anticipated objections instead of directly "
            f"stating what was done — a common AI writing-style tell that lowers information "
            f"density. This is a STYLE IMPRESSION with ZERO verdict weight, not a factual "
            f"inconsistency and not an authorship verdict. If a specific hedge instead reveals a "
            f"real scope/evaluation limitation, that is a separate integrity finding "
            f"(HP-SCOPE-INFLATE / eval-design-forensics)."),
        "severity": "minor",                          # adjudicator forces AIS to info, weight 0
        "observability_level_required": 0,
        "evidence": evidence,
        "verdict_local": "warn",
        "reviewer": {"deterministic": True},
        "false_positive_risk": "high",
        "not_integrity_finding": True,
        "fp_case": (
            "Some venues / AI reviewers penalize the ABSENCE of caveats, so measured hedging is "
            "a legitimate strategic choice; a single scoping sentence is not the pattern."),
        "recommended_reviewer_action": (
            "Skim the cited sentences: if the paper over-hedges in its contribution/body, that "
            "lowers readability. Impression only — not misconduct, not an authorship judgment."),
    }]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic AI writing-style impression checks (AIS).")
    ap.add_argument("--ledger", required=True, help="claims.json from build_claim_ledger.py")
    ap.add_argument("--out", default="ai-style-impressions.deterministic.findings.json")
    args = ap.parse_args(argv)

    with open(args.ledger, "r", encoding="utf-8") as fh:
        ledger = json.load(fh)
    claims = ledger.get("claims", [])
    findings = check_defensive_hedge(claims)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2, ensure_ascii=False)
    n_hedge = sum(1 for f in findings if f["pattern_id"] == "AIS-DEFENSIVE-HEDGE")
    print(f"AI-style impressions: {len(findings)} ({n_hedge} defensive-hedge) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
