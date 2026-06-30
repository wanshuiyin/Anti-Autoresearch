#!/usr/bin/env python3
"""
Unit tests for the deterministic AI writing-style screen (AIS track) — focused on the
AIS-DEFENSIVE-HEDGE density screen's FALSE-POSITIVE boundaries (the part most likely to
over-fire). They lock in: it fires ONLY on a real pattern (>=4 distinct hedge sentences
across >=2 non-excluded sections AND >=25% of scope sentences), collapses duplicates, never
counts hedges in Limitations / Related-Work / Ethics, stays in sync with the ledger's capture
net, and emits a zero-weight AIS impression (skill ai-style-impressions, pattern AIS-*).

Run: python3 tests/test_ai_style.py   (also pytest-compatible)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
sys.path.insert(0, os.path.join(HERE, "..", "eval"))
import check_ai_style as A  # noqa: E402
import build_claim_ledger as L  # noqa: E402

# four distinct strong hedges across two non-excluded sections — the firing pattern.
# These mirror eval/corrupt.py's `defensive_hedge` injection verbatim (test_corruption_*
# enforces that), so the boundary tests exercise exactly what the eval does.
HEDGES = [
    ("introduction", "We do not claim that this routing module is optimal."),
    ("introduction", "This does not mean that simpler designs cannot work."),
    ("method", "We are not proposing a fundamentally new architecture."),
    ("method", "Our goal is not to maximize raw accuracy, but rather to isolate the routing effect."),
]


def _claim(cid, section, text):
    return {"claim_id": cid, "type": "scope", "text_span": text,
            "location": {"file": "p.tex", "section": section}, "evidence_anchor": "h"}


def test_fires_on_pattern():
    out = A.check_defensive_hedge([_claim(f"C{i}", s, t) for i, (s, t) in enumerate(HEDGES)])
    assert len(out) == 1 and out[0]["pattern_id"] == "AIS-DEFENSIVE-HEDGE", out
    assert out[0]["skill"] == "ai-style-impressions"
    assert out[0]["not_integrity_finding"] is True
    assert out[0]["false_positive_risk"] == "high"
    assert all((e.get("span") or "").strip() for e in out[0]["evidence"]), "must be anchored"


def test_below_min_sentences_silent():
    assert A.check_defensive_hedge(
        [_claim(f"C{i}", s, t) for i, (s, t) in enumerate(HEDGES[:3])]) == []


def test_single_section_silent():
    assert A.check_defensive_hedge(
        [_claim(f"C{i}", "introduction", t) for i, (_s, t) in enumerate(HEDGES)]) == []


def test_excluded_sections_not_counted():
    claims = [_claim(f"C{i}", "limitations", t) for i, (_s, t) in enumerate(HEDGES)]
    claims += [_claim(f"R{i}", "related work", t) for i, (_s, t) in enumerate(HEDGES)]
    assert A.check_defensive_hedge(claims) == []


def test_duplicates_collapse():
    dup = [_claim("C0", "introduction", HEDGES[0][1]),
           _claim("C0b", "introduction", HEDGES[0][1]),
           _claim("C2", "method", HEDGES[2][1]),
           _claim("C2b", "method", HEDGES[2][1])]
    assert A.check_defensive_hedge(dup) == []


def test_clean_single_scoping_sentence_silent():
    assert A.check_defensive_hedge(
        [_claim("C0", "body", "We make no claim of broad generality.")]) == []


def test_bare_not_but_rather_is_not_a_hedge():
    # a normal technical contrast ("not X but rather Y") WITHOUT author/paper stance must not count
    techs = ["The operator is not convex but rather piecewise smooth.",
             "The bound is not tight but rather loose.",
             "The model is not linear but rather nonlinear.",
             "The signal is not stationary but rather time-varying."]
    claims = [_claim(f"C{i}", "introduction" if i < 2 else "method", t)
              for i, t in enumerate(techs)]
    assert A.check_defensive_hedge(claims) == []


def test_ratio_gate_suppresses_sparse_hedges():
    claims = [_claim(f"H{i}", s, t) for i, (s, t) in enumerate(HEDGES)]
    for i in range(13):
        claims.append(_claim(f"S{i}", "introduction" if i % 2 else "method",
                             f"We report comprehensive results on benchmark {i}."))
    assert A.check_defensive_hedge(claims) == []


def test_ledger_cue_and_detector_in_sync():
    """Drift guard: every injected hedge must be matched by a strict DEFENSIVE_HEDGE_PATTERNS
    template AND caught by build_claim_ledger.HEDGE_CUES (so it reaches the ledger to anchor)."""
    rx = [re.compile(p, re.IGNORECASE) for p in A.DEFENSIVE_HEDGE_PATTERNS]
    for _sec, sent in HEDGES:
        assert any(r.search(sent) for r in rx), f"no strict template matches: {sent!r}"
        assert L.HEDGE_CUES.search(sent), f"HEDGE_CUES misses (won't reach ledger): {sent!r}"


def test_corruption_uses_these_hedges():
    """Drift guard: the eval corruption must keep injecting exactly these sentences."""
    import corrupt
    repl = " ".join(r for _find, r in corrupt.CORRUPTIONS["defensive_hedge"])
    for _sec, sent in HEDGES:
        assert sent in repl, f"corrupt.py defensive_hedge drifted from the tests: {sent!r}"


def test_borrowed_patterns_in_sync():
    """Patterns cross-referenced from anti-defensive-writing (MIT) must each be matched by a
    DEFENSIVE_HEDGE_PATTERNS template AND caught by build_claim_ledger.HEDGE_CUES (so they
    reach the ledger as scope claims), and stay stance-constrained (no bare technical contrast)."""
    rx = [re.compile(p, re.IGNORECASE) for p in A.DEFENSIVE_HEDGE_PATTERNS]
    hits = [
        "This is not to say that simpler models are useless.",
        "This should not be taken to mean that the method always wins.",
        "Rather than arguing for a new paradigm, this paper argues for a small fix.",
        "The goal of this paper is not to maximize accuracy but to isolate the effect.",
    ]
    for s in hits:
        assert any(r.search(s) for r in rx), f"no strict template matches: {s!r}"
        assert L.HEDGE_CUES.search(s), f"HEDGE_CUES misses (won't reach ledger): {s!r}"
    # stance guard: a bare technical "rather than X, Y" with no author subject must NOT match
    assert not any(r.search("Rather than convexity, the operator assumes smoothness.") for r in rx)
    # "not only ... but also" is legitimate contribution framing, NOT defensive hedging
    assert not any(r.search(
        "The goal of this paper is not only to describe the method but also to evaluate it.") for r in rx)
    assert not any(r.search(
        "Our goal is not only to maximize accuracy but also to stay interpretable.") for r in rx)


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run()
