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

# --- HP-DEFENSIVE-HEDGE -------------------------------------------------------------
# A DENSITY screen for defensive "we do not claim … / not X but rather Y" writing — the
# rhetorical posture of defending against anticipated objections instead of stating what
# was done. UNLIKE HP-PIPELINE-ARTIFACT this is NOT a low-FP exact match: one scoping
# sentence is legitimate (and a Limitations section SHOULD hedge). So this is a deliberately
# CONSERVATIVE sieve — it fires ONLY on a genuine pattern (many STRONG hedges across
# multiple non-excluded sections), is capped at minor like every family-F signal, and flags
# the RECURRENCE of the shape, never who wrote it (no stylometry, no authorship/AI verdict).
# Keep these strict templates a SUBSET of build_claim_ledger.HEDGE_CUES — that recall-net is
# what gets pure-prose hedges into the ledger so this screen has anchored spans to cite.
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


def check_defensive_hedge(claims, start=0):
    """Deterministic family-F DENSITY screen for defensive-hedge writing
    (HP-DEFENSIVE-HEDGE). Scans ledger claim spans for STRONG defensive templates and
    fires ONE finding only when the paper shows a genuine pattern: at least
    HEDGE_MIN_SENTENCES distinct hedge sentences spread across at least HEDGE_MIN_SECTIONS
    non-excluded sections. Conservative by design (precision >> recall), capped at minor by
    the adjudicator's SURFACE gate, and NEVER an authorship/AI-generation verdict — it flags
    the recurrence of the hedge SHAPE only. Hits in limitations/related-work/ethics sections
    are not counted (a hedge there is expected). ``start`` offsets the PRES### id counter so
    it shares a namespace with the other presentation checks collision-free."""
    rx = [re.compile(p, re.IGNORECASE) for p in DEFENSIVE_HEDGE_PATTERNS]
    seen_scope, scope_total = set(), 0     # distinct non-excluded `scope` claims (the denominator)
    seen_hit, hits = set(), []
    for c in claims:
        # Only `scope`-language claims (precision): a hedge that also carries a number/citation
        # still gets its OWN scope claim from build_claim_ledger.HEDGE_CUES, so nothing is lost —
        # and we avoid scanning every numeric sentence for a stray "not … but".
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
    # Fire ONLY on a genuine pattern: enough distinct hedges, spread across sections, AND a
    # high-enough share of the paper's scope language (so a few scattered caveats in a long
    # honest paper stay below threshold). NB: PDF-only ledgers carry section "unknown" for every
    # claim, so the >=2-section gate makes this effectively LaTeX-decided — conservative by design.
    if (len(hits) < HEDGE_MIN_SENTENCES or len(sections) < HEDGE_MIN_SECTIONS
            or len(hits) < HEDGE_MIN_RATIO * scope_total):
        return []
    evidence = [{"claim_id": h["claim_id"], "span": h["span"], "location": h["location"],
                 "artifact_hash": h["anchor"]} for h in hits[:3]]
    sec_list = ", ".join(sorted(s for s in sections if s)) or "multiple sections"
    return [{
        "finding_id": f"PRES{start + 1:03d}",
        "skill": "presentation-signals",
        "pattern_id": "HP-DEFENSIVE-HEDGE",
        "title": "Pervasive defensive-hedge writing across multiple sections",
        "description": (
            f"{len(hits)} distinct defensive-hedge constructions (e.g. \"we do not claim …\", "
            f"\"not X but rather Y\") across {len(sections)} non-excluded sections ({sec_list}). "
            f"The text repeatedly defends against anticipated objections instead of directly "
            f"stating what was done, which lowers information density and can flag attack "
            f"surface to a reviewer. The checkable signal is the RECURRENCE of the hedge shape "
            f"— NOT who wrote it: this is not stylometry and not an authorship/AI-generation "
            f"verdict. If a specific hedge instead reveals a real scope/evaluation limitation, "
            f"route THAT to HP-SCOPE-INFLATE / eval-design-forensics (substantive), not this "
            f"surface signal."),
        "severity": "minor",                          # capped (family F); SURFACE gate
        "observability_level_required": 0,
        "evidence": evidence,
        "verdict_local": "warn",
        "reviewer": {"deterministic": True},
        "false_positive_risk": "high",
        "recommended_reviewer_action": (
            "Skim the cited sentences: if the paper over-hedges in its contribution/body "
            "(rather than confining caveats to a single Limitations paragraph), suggest "
            "stating results directly. This is a presentation signal, not evidence of "
            "misconduct or AI authorship; hedges in Limitations/Related-Work are excluded."),
    }]


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
    findings += check_defensive_hedge(claims, start=len(findings))      # share PRES### ids
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2, ensure_ascii=False)
    n_dup = sum(1 for f in findings if f["pattern_id"] == "HP-DUP-TABLE")
    n_pipe = sum(1 for f in findings if f["pattern_id"] == "HP-PIPELINE-ARTIFACT")
    n_hedge = sum(1 for f in findings if f["pattern_id"] == "HP-DEFENSIVE-HEDGE")
    print(f"presentation findings: {len(findings)} "
          f"({n_dup} dup-table, {n_pipe} pipeline-artifact, {n_hedge} defensive-hedge) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
