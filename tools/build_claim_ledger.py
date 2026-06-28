#!/usr/bin/env python3
"""
build_claim_ledger.py — deterministic evidence-ledger extractor.

Turns a paper's source into schemas/claims.json: a span-anchored list of every
checkable claim (numbers, comparisons, scope language, citations, captions, table
cells). This is the ONLY structure the auditor skills are allowed to reason over —
no auditor re-reads the raw paper and invents structure (integrity-forensics-
contract.md). LaTeX-first (stable spans + line numbers); a plain-text path exists
for PDF-extracted text at lower confidence.

Pure standard library. Best-effort regex extraction; the goal is high recall on
the *checkable* surface, with honest `confidence` tags so the adjudicator and
human can weight low-confidence (PDF/OCR) numbers accordingly.
"""
import argparse
import hashlib
import json
import re
import sys

LEDGER_VERSION = "0.1"

SCOPE_WORDS = re.compile(
    r"\b(comprehensive|extensive|exhaustive|robust|robustly|consistently|"
    r"state[- ]of[- ]the[- ]art|SOTA|outperform\w*|significantly|substantially|"
    r"general(?:ly|izes)?|always|all (?:tasks|datasets|settings)|first to)\b",
    re.IGNORECASE,
)
# Defensive-hedge cues: a *recall-oriented* net so sentences that defend against an
# anticipated objection ("we do not claim ...", "this does not mean ...", "目的不是…而是…")
# land in the ledger as `scope` claims even when they carry no number/citation. The
# strict precision list that DECIDES AIS-DEFENSIVE-HEDGE (and its count/section gate) lives
# in tools/check_ai_style.py (DEFENSIVE_HEDGE_PATTERNS); keep that a subset of this.
# This is scope language, not a verdict: capturing it here only makes it anchorable.
HEDGE_CUES = re.compile(
    r"(we (?:do|are|did|will) not (?:claim|argu|propos|aim|seek|intend|mean|attempt|suggest)\w*|"
    r"we make no claim|this (?:does|did|should) not (?:mean|impl|suggest)\w*|"
    r"our (?:goal|aim|purpose|intention|objective) is not|"
    r"\b(?:we|this (?:paper|work|study))\b[^.;:]{0,40}\bnot\b[^.;:]{1,40}\bbut rather\b|"
    r"本文(?:并)?不(?:声称|主张|是要|旨在)|并不声称|并不主张|这并不意味|目的不是)",
    re.IGNORECASE,
)
NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(\\?%|percent|points?|pts?|x|×)?")
CITE = re.compile(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")
CAPTION = re.compile(r"\\caption\*?\{")
METRIC = re.compile(
    r"\b(accuracy|acc|F1|F-?1|BLEU|ROUGE|exact match|EM|precision|recall|AUC|"
    r"perplexity|PPL|latency|throughput|win[- ]rate|pass@\d+|mAP|IoU|MSE|RMSE|MAE|"
    r"success rate|reward|score)\b",
    re.IGNORECASE,
)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_sentences(paragraph):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\\])", paragraph)
    return [p.strip() for p in parts if p.strip()]


def iter_paragraphs(lines):
    """Yield (text, start_line, end_line) for blank-line-separated paragraphs."""
    buf, start, end = [], None, None
    for i, ln in enumerate(lines, 1):
        if ln.strip() == "":
            if buf:
                yield " ".join(buf), start, end
                buf, start, end = [], None, None
        else:
            if start is None:
                start = i
            end = i
            buf.append(ln.strip())
    if buf:
        yield " ".join(buf), start, end


def section_tracker(lines):
    marks = []
    tbl = fig = 0
    in_abstract = False
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        m = re.match(r"\\(sub)*section\*?\{([^}]*)\}", s)
        if m:
            marks.append((i, m.group(2).strip().lower()))
        if "\\begin{abstract}" in s:
            marks.append((i, "abstract")); in_abstract = True
        if "\\end{abstract}" in s and in_abstract:
            marks.append((i, "intro")); in_abstract = False
        if "\\begin{table" in s:
            tbl += 1; marks.append((i, f"table:{tbl}"))
        if "\\end{table" in s:
            marks.append((i, "body"))
        if "\\begin{figure" in s:
            fig += 1; marks.append((i, f"figure:{fig}"))
        if "\\end{figure" in s:
            marks.append((i, "body"))
        if re.search(r"\\(begin\{appendix\}|appendix)\b", s):
            marks.append((i, "appendix"))
    marks.sort()

    def label(line_no):
        cur = "body"
        for ln_no, lab in marks:
            if ln_no <= line_no:
                cur = lab
            else:
                break
        return cur
    return label


def in_tabular(lines):
    inside, depth = set(), 0
    for i, ln in enumerate(lines, 1):
        if "\\begin{tabular" in ln:
            depth += 1
        if depth > 0:
            inside.add(i)
        if "\\end{tabular" in ln:
            depth = max(0, depth - 1)
    return inside


def parse_value(num_str, unit):
    try:
        norm = float(num_str)
    except ValueError:
        norm = None
    u = None
    if unit:
        if "%" in unit or unit.lower() == "percent":
            u = "%"
        elif unit.lower().startswith(("point", "pt")):
            u = "point"
        elif unit in ("x", "×"):
            u = "x"
        else:
            u = unit
    return {"raw": num_str, "normalized": norm, "unit": u}


def _local_metric(sent, start, end):
    """Bind a metric keyword to THIS number (just before or after it: catches both
    '78.0% accuracy' and 'accuracy of 78.0%'), without crossing a clause boundary —
    so 'X% accuracy, a Y% improvement' does NOT tag Y with accuracy."""
    before = re.split(r"[,;:]", sent[max(0, start - 18): start])[-1]
    after = re.split(r"[,;:.]", sent[end: end + 22])[0]
    local = before + sent[start:end] + after
    m = METRIC.search(local)
    return m.group(0).lower() if m else None


def _num_value(num, unit, sent, mstart, mend):
    return {**parse_value(num, unit),
            "metric": _local_metric(sent, mstart, mend),
            "direction": "unknown", "aggregation": "unspecified"}


def extract_from_latex(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    anchor = sha256_text(text)
    lines = text.splitlines()
    label = section_tracker(lines)
    tab_lines = in_tabular(lines)
    claims = []

    # 1) table cells: line-based (inside tabular only)
    for i, ln in enumerate(lines, 1):
        if i not in tab_lines or ln.strip().startswith("%"):
            continue
        sec = label(i)
        for m in NUMBER.finditer(ln):
            num, unit = m.group(1), m.group(2)
            # keep bare integers in tables too (integer-valued result tables are
            # common); the lookbehind already excludes digits glued to words/years.
            claims.append({
                "type": "table_cell",
                "text_span": ln.strip()[:300],
                "location": {"file": path, "line": i, "section": sec},
                "value": _num_value(num, unit, ln, m.start(1), m.end()),
                "evidence_anchor": anchor,
                "extractor": "table_parser",
                "confidence": "medium",
            })

    # 2) prose: sentence-based spans (numbers, citations, scope); captions
    for para, start, end in iter_paragraphs(lines):
        sec = label(start)
        is_table_para = any(j in tab_lines for j in range(start, end + 1))
        if not is_table_para:
            for sent in split_sentences(para):
                for m in NUMBER.finditer(sent):
                    num, unit = m.group(1), m.group(2)
                    if not unit and "." not in num and not METRIC.search(sent):
                        continue
                    claims.append({
                        "type": "number",
                        "text_span": sent[:400],
                        "location": {"file": path, "line": start, "section": sec},
                        "value": _num_value(num, unit, sent, m.start(1), m.end()),
                        "evidence_anchor": anchor,
                        "extractor": "latex_regex",
                        "confidence": "high",
                    })
                for cm in CITE.finditer(sent):
                    keys = [k.strip() for k in cm.group(1).split(",") if k.strip()]
                    claims.append({
                        "type": "citation", "text_span": sent[:400],
                        "location": {"file": path, "line": start, "section": sec},
                        "refs": keys, "evidence_anchor": anchor,
                        "extractor": "latex_regex", "confidence": "high",
                    })
                if SCOPE_WORDS.search(sent) or HEDGE_CUES.search(sent):
                    claims.append({
                        "type": "scope", "text_span": sent[:400],
                        "location": {"file": path, "line": start, "section": sec},
                        "evidence_anchor": anchor, "extractor": "latex_regex",
                        "confidence": "high",
                    })
        if CAPTION.search(para):
            cap = para[para.find("\\caption"):][:400]
            claims.append({
                "type": "caption", "text_span": cap,
                "location": {"file": path, "line": start, "section": sec},
                "evidence_anchor": anchor, "extractor": "latex_regex",
                "confidence": "medium",
            })
    return claims, anchor


def extract_from_text(path):
    """Lower-confidence path for PDF-extracted plain text (no reliable lines)."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    anchor = sha256_text(text)
    claims = []
    for para in re.split(r"\n\s*\n", text):
        for sent in split_sentences(para.replace("\n", " ")):
            for m in NUMBER.finditer(sent):
                num, unit = m.group(1), m.group(2)
                if not unit and "." not in num and not METRIC.search(sent):
                    continue
                claims.append({
                    "type": "number", "text_span": sent[:300],
                    "location": {"file": path, "section": "unknown"},
                    "value": _num_value(num, unit, sent, m.start(1), m.end()),
                    "evidence_anchor": anchor, "extractor": "pdf_text",
                    "confidence": "low",
                })
            if SCOPE_WORDS.search(sent) or HEDGE_CUES.search(sent):
                claims.append({"type": "scope", "text_span": sent[:400],
                               "location": {"file": path, "section": "unknown"},
                               "evidence_anchor": anchor, "extractor": "pdf_text",
                               "confidence": "low"})
    return claims, anchor


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the evidence ledger (claims.json).")
    ap.add_argument("--paper-id", required=True)
    ap.add_argument("--latex", nargs="*", default=[], help="LaTeX source file(s)")
    ap.add_argument("--pdf-text", nargs="*", default=[], help="plain-text PDF extraction(s)")
    ap.add_argument("--observability-level", type=int, default=1, choices=[0, 1, 2, 3])
    ap.add_argument("--generated-at", default="")
    ap.add_argument("--out", default="claims.json")
    args = ap.parse_args(argv)

    if not args.latex and not args.pdf_text:
        ap.error("provide at least one --latex or --pdf-text source")

    all_claims, sources = [], []
    for p in args.latex:
        cl, anchor = extract_from_latex(p)
        all_claims += cl
        sources.append({"path": p, "sha256": anchor, "kind": "latex"})
    for p in args.pdf_text:
        cl, anchor = extract_from_text(p)
        all_claims += cl
        sources.append({"path": p, "sha256": anchor, "kind": "text"})

    out_claims = []
    for idx, c in enumerate(all_claims, 1):
        out_claims.append({"claim_id": f"C{idx:03d}", **c})

    ledger = {
        "ledger_version": LEDGER_VERSION,
        "paper_id": args.paper_id,
        "observability_level": args.observability_level,
        "generated_at": args.generated_at or "",
        "source_files": sources,
        "claims": out_claims,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2, ensure_ascii=False)
    by_type = {}
    for c in out_claims:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    print(f"ledger: {len(out_claims)} claims {dict(sorted(by_type.items()))} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
