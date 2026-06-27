#!/usr/bin/env python3
"""
check_presentation.py — deterministic surface-signal checks.

These are the *presentation*-level signals (the cluster-A "AI-flavor / low-effort"
family) that can be computed without a model. Ships the two objective, eval-testable
ones: duplicate/near-identical tables (HP-DUP-TABLE) and exact-match leftover
pipeline/assistant/template strings (HP-PIPELINE-ARTIFACT).

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

# --- HP-PIPELINE-ARTIFACT -----------------------------------------------------------
# Exact-match leftover pipeline/assistant/template strings that must never survive into
# a finished paper. CASE-INSENSITIVE substring match — this is NOT stylometry and NOT a
# classifier: we flag the verbatim STRING, never who/what produced the text (the textual
# analog of HP-PLACEHOLDER-DATA). That is exactly why this is the one LOW-FP family-F
# pattern. Inclusion bar: a phrase qualifies ONLY if it is essentially never legitimate
# in finished paper body prose. When in doubt, leave it out — precision >> recall.
PIPELINE_ARTIFACT_PHRASES = (
    # assistant / chat-model refusal & self-reference leftovers
    # ("ChatGPT fingerprint" family; Problematic Paper Screener: Cabanac, Labbé & Magazinov)
    "as an ai language model",
    "as a large language model",
    "as an ai assistant",
    "i'm sorry, but i cannot",
    "i cannot fulfill",
    "i cannot fulfil",            # British spelling
    "i am unable to provide",
    "as of my last knowledge update",
    "regenerate response",
    # editor / template placeholders never meant to ship. NOTE: if such a placeholder
    # actually FEEDS a reported number/figure it is HP-PLACEHOLDER-DATA (family D,
    # critical), not this surface pattern — route there.
    "<your text here>",
    "[insert ",                   # catches "[INSERT X]", "[Insert citation]"
    "<insert ",
    "todo: cite",
    "todo: add citation",
    "[citation needed]",
    "lorem ipsum",
    # (NB: phrases like "click here to" were considered and REJECTED — they occur in
    # legitimate HCI / web / accessibility prose. Precision >> recall: when in doubt, leave out.)
)


def _anchorable(s):
    """Mirror the adjudicator's `_anchorable` on the WHITESPACE-NORMALIZED span (the
    adjudicator normalizes whitespace before checking), so our window-sizing matches
    what will actually anchor: >=1 alphanumeric AND (>=12 chars OR >=3 word tokens)."""
    nw = " ".join((s or "").split())
    if not any(ch.isalnum() for ch in nw):
        return False
    return len(nw) >= 12 or len(nw.split()) >= 3


def _anchor_window(text, start, end, pad=28):
    """Return a verbatim slice of ``text`` around the [start, end) hit, padded so it
    clears the adjudicator's anchor gate where possible. ``.strip()`` only trims the
    ends, so the result stays a contiguous substring of ``text`` (and still contains the
    hit). Best-effort: if neither the padded window nor the whole claim is anchorable (a
    tiny standalone claim), return the whole claim and let the adjudicator correctly
    demote the finding to info — fail-closed, never a non-substring."""
    win = text[max(0, start - pad): min(len(text), end + pad)].strip()
    if _anchorable(win):
        return win
    return text.strip()


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


def check_pipeline_artifacts(claims, start=0):
    """Deterministic family-F surface check: an EXACT-MATCH leftover pipeline/assistant/
    template string in any extracted claim's text (HP-PIPELINE-ARTIFACT). Emits one
    finding per distinct (physical text span, phrase) hit. Flags the checkable string
    ONLY — it NEVER infers AI authorship (exact substring match, no stylometry, no
    classifier), which is why it is the one LOW-FP F-pattern. Still capped at ``minor``
    by the adjudicator's SURFACE gate, like every family-F signal. ``start`` offsets the
    PRES### id counter so it shares a namespace with check_duplicate_tables collision-free.
    """
    findings, seen, n = [], set(), 0
    for c in claims:
        span_text = c.get("text_span")
        if not isinstance(span_text, str) or not span_text:
            continue
        loc = c.get("location", {})
        for phrase in PIPELINE_ARTIFACT_PHRASES:
            # re.finditer on the ORIGINAL text with IGNORECASE: correct indices even when
            # .lower() would change length (Unicode), and finds every occurrence.
            for m in re.finditer(re.escape(phrase), span_text, re.IGNORECASE):
                hit = m.group(0)                              # verbatim, original casing
                # dedup per (location, normalized-text, phrase): the SAME physical text
                # captured under >1 claim type collapses, but the SAME text at a DIFFERENT
                # location stays a distinct leftover and still fires.
                key = (loc.get("file"), loc.get("section"), loc.get("line"),
                       " ".join(span_text.split()), phrase)
                if key in seen:
                    continue
                seen.add(key)
                n += 1
                window = _anchor_window(span_text, m.start(), m.end())
                findings.append({
                    "finding_id": f"PRES{start + n:03d}",
                    "skill": "presentation-signals",
                    "pattern_id": "HP-PIPELINE-ARTIFACT",
                    "title": "Leftover pipeline/assistant string in finished text",
                    "description": (
                        f'The exact phrase "{hit}" appears in '
                        f"{loc.get('section', '?')} (claim {c.get('claim_id')}). This is a "
                        f"verbatim pipeline/template leftover that should not survive into a "
                        f"finished paper. The check flags the CHECKABLE STRING only — it does "
                        f"NOT infer who or what produced the text (exact substring match, not "
                        f"stylometry, not an AI-text classifier). If this string instead "
                        f"FEEDS a reported number/figure, it is HP-PLACEHOLDER-DATA "
                        f"(family D, critical), not this surface signal."),
                    "severity": "minor",                      # capped (family F); SURFACE gate
                    "observability_level_required": 0,
                    "evidence": [
                        {"claim_id": c.get("claim_id"), "span": window, "location": loc,
                         "artifact_hash": c.get("evidence_anchor", "")},
                    ],
                    "verdict_local": "warn",
                    "reviewer": {"deterministic": True},
                    "false_positive_risk": "low",             # the one LOW-FP F-pattern
                    "recommended_reviewer_action": (
                        "Confirm the string is a genuine leftover and not a deliberate "
                        "quotation/discussion of such text (e.g. a paper studying LLM "
                        "outputs / refusal messages); if it is a leftover, the text should be "
                        "cleaned. This is a surface signal, not an authorship or misconduct "
                        "finding."),
                })
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic surface-signal checks.")
    ap.add_argument("--ledger", required=True, help="claims.json from build_claim_ledger.py")
    ap.add_argument("--out", default="presentation-signals.deterministic.findings.json")
    args = ap.parse_args(argv)

    with open(args.ledger, "r", encoding="utf-8") as fh:
        ledger = json.load(fh)
    claims = ledger.get("claims", [])
    findings = check_duplicate_tables(claims)
    findings += check_pipeline_artifacts(claims, start=len(findings))   # share PRES### ids
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2, ensure_ascii=False)
    n_dup = sum(1 for f in findings if f["pattern_id"] == "HP-DUP-TABLE")
    n_pipe = sum(1 for f in findings if f["pattern_id"] == "HP-PIPELINE-ARTIFACT")
    print(f"presentation findings: {len(findings)} "
          f"({n_dup} dup-table, {n_pipe} pipeline-artifact) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
