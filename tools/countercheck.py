#!/usr/bin/env python3
"""
countercheck.py — deterministic counter-check resolvers (issue #15).

The ONLY path that may ever demote a critical (doctrine from #14: model outputs are
markers; only computations change severity). A resolver PROVES, by interval
arithmetic over the DISPLAYED precision of the very numbers the accusation cites,
that the accused discrepancy cannot be established from the evidence — e.g. a
"wrong delta" that is exactly what display rounding of the operands permits.

Design rules (from the cross-model design review):
- Pure stdlib, `decimal.Decimal` throughout — binary `round()` is forbidden.
- OPEN rounding intervals: a displayed value x with d decimals stands for the open
  interval (x − ½·10⁻ᵈ, x + ½·10⁻ᵈ). Endpoint contact proves nothing under an
  unknown rounding mode (half-up vs half-even) → UNRESOLVABLE, never a demotion.
- The resolver receives ONLY ledger-derived raw strings (the adjudicator re-derives
  them from claims.json; nothing model-supplied reaches a computation).
- Every ambiguity — scientific notation, thousands separators, unit mismatch,
  denominator interval crossing zero, no explicit convention marker — returns
  UNRESOLVABLE. Only PROVED_COMPATIBLE may demote.

Statuses:
  PROVED_COMPATIBLE    — the accusation's numeric basis is fully explained by
                         display rounding; the discrepancy provably cannot be
                         established from these numbers.
  DISCREPANCY_PERSISTS — the computation confirms the numbers cannot be reconciled.
  UNRESOLVABLE         — the computation cannot decide (ambiguity / endpoint contact).
"""
import re
from decimal import Decimal, getcontext

getcontext().prec = 50

COUNTERCHECK_VERSION = "1.0"

PROVED_COMPATIBLE = "PROVED_COMPATIBLE"
DISCREPANCY_PERSISTS = "DISCREPANCY_PERSISTS"
UNRESOLVABLE = "UNRESOLVABLE"

_SIMPLE_NUM = re.compile(r"^-?\d+(\.\d+)?$")
_POINTS_MARKER = re.compile(r"\b(points?|pp)\b", re.I)
_RELATIVE_MARKER = re.compile(r"\brelative\b", re.I)


def decimals_of(raw):
    """Displayed decimal places of a plain numeral string; None when the string is
    not a simple decimal numeral (scientific notation, separators, ranges...)."""
    raw = (raw or "").strip()
    if not _SIMPLE_NUM.match(raw):
        return None
    return len(raw.split(".")[1]) if "." in raw else 0


def display_interval(raw):
    """Open interval a displayed numeral stands for, or None if unresolvable."""
    d = decimals_of(raw)
    if d is None:
        return None
    x = Decimal(raw)
    half = Decimal(5) / (Decimal(10) ** (d + 1))
    return (x - half, x + half)


def _open_intervals_intersect(a, b):
    """Strict intersection of two open intervals; endpoint contact is False."""
    return max(a[0], b[0]) < min(a[1], b[1])


def delta_convention_from_span(span):
    """The stated delta's convention must be EXPLICIT in the claim's own words —
    a bare "improves by X%" may not pick whichever convention rescues it."""
    span = span or ""
    points = bool(_POINTS_MARKER.search(span))
    relative = bool(_RELATIVE_MARKER.search(span))
    if points and not relative:
        return "points"
    if relative and not points:
        return "relative"
    return None


def rounding_interval_delta(old_raw, new_raw, stated_raw, convention,
                            old_unit=None, new_unit=None):
    """HP-DELTA-ERROR resolver: could true values inside the operands' display
    intervals produce a delta that displays as the stated value?

    convention: "relative" → (new−old)/old·100 ; "points" → new−old.
    Returns (status, evidence_dict)."""
    ev = {"resolver": "rounding_interval", "version": COUNTERCHECK_VERSION,
          "convention": convention,
          "inputs": {"old": old_raw, "new": new_raw, "stated": stated_raw}}
    if convention not in ("relative", "points"):
        return UNRESOLVABLE, dict(ev, why="convention not explicit in the stated span")
    if (old_unit or None) != (new_unit or None):
        return UNRESOLVABLE, dict(ev, why=f"operand units differ: {old_unit!r} vs {new_unit!r}")
    io, inw, ist = (display_interval(old_raw), display_interval(new_raw),
                    display_interval(stated_raw))
    if not (io and inw and ist):
        return UNRESOLVABLE, dict(ev, why="a value is not a plain decimal numeral")
    if convention == "points":
        achievable = (inw[0] - io[1], inw[1] - io[0])
    else:
        if io[0] <= 0 <= io[1]:
            return UNRESOLVABLE, dict(ev, why="denominator interval contains zero")
        corners = [(nv / ov - 1) * 100 for nv in (inw[0], inw[1]) for ov in (io[0], io[1])]
        achievable = (min(corners), max(corners))
    ev["achievable_interval"] = [str(achievable[0]), str(achievable[1])]
    ev["stated_interval"] = [str(ist[0]), str(ist[1])]
    if _open_intervals_intersect(achievable, ist):
        return PROVED_COMPATIBLE, ev
    if max(achievable[0], ist[0]) == min(achievable[1], ist[1]):
        return UNRESOLVABLE, dict(ev, why="endpoint contact — rounding mode unknown")
    return DISCREPANCY_PERSISTS, ev


def display_precision(fine_raw, coarse_raw, fine_unit=None, coarse_unit=None):
    """HP-NUM-INFLATE / HP-APPENDIX-CONTRA resolver: are two displays of the same
    quantity at different precisions mutually consistent? True iff their open
    display intervals strictly intersect. Returns (status, evidence_dict)."""
    ev = {"resolver": "display_precision", "version": COUNTERCHECK_VERSION,
          "inputs": {"fine": fine_raw, "coarse": coarse_raw}}
    if (fine_unit or None) != (coarse_unit or None):
        return UNRESOLVABLE, dict(ev, why=f"units differ: {fine_unit!r} vs {coarse_unit!r}")
    fi, ci = display_interval(fine_raw), display_interval(coarse_raw)
    if not (fi and ci):
        return UNRESOLVABLE, dict(ev, why="a value is not a plain decimal numeral")
    ev["fine_interval"] = [str(fi[0]), str(fi[1])]
    ev["coarse_interval"] = [str(ci[0]), str(ci[1])]
    if _open_intervals_intersect(fi, ci):
        return PROVED_COMPATIBLE, ev
    if max(fi[0], ci[0]) == min(fi[1], ci[1]):
        return UNRESOLVABLE, dict(ev, why="endpoint contact — rounding mode unknown")
    return DISCREPANCY_PERSISTS, ev


# pattern_id -> (resolver name, required numeric_basis roles)
ALLOWLIST = {
    "HP-DELTA-ERROR": ("rounding_interval", frozenset({"old", "new", "stated"})),
    "HP-NUM-INFLATE": ("display_precision", frozenset({"fine", "coarse"})),
    "HP-APPENDIX-CONTRA": ("display_precision", frozenset({"fine", "coarse"})),
}
