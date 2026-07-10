#!/usr/bin/env python3
"""
countercheck.py — deterministic counter-check resolvers (issue #15).

The ONLY path that may ever demote a critical (doctrine from #14: model outputs are
markers; only computations change severity). A resolver PROVES, by exact interval
arithmetic over the DISPLAYED precision of the very numbers the accusation cites,
that the accused discrepancy cannot be established from the evidence.

Demotion-authorization rule (the load-bearing line, from the cross-model review):
**a resolver may demote only when its verdict is invariant under every
model-controlled degree of freedom.**

- `display_precision` (HP-NUM-INFLATE, HP-APPENDIX-CONTRA): "do the two open
  display intervals strictly intersect" is SYMMETRIC — swapping the model-assigned
  fine/coarse roles cannot change the answer, and the completeness rule pins the
  claim set. Verdict is binding-invariant → MAY demote.
- `rounding_interval` (HP-DELTA-ERROR): (new−old)/old·100 is NOT symmetric in
  old/new, and no deterministic parser can certify which operand is the baseline —
  a role swap can flip the verdict. So this resolver is REPORT-ONLY: its result is
  recorded on the finding (certified: false) for the human, and it can NEVER
  demote, whatever it concludes.

Numeric rules:
- Pure stdlib, `fractions.Fraction` — EXACT rational arithmetic. No floating
  point, no fixed Decimal precision (a 50-digit operand cannot smuggle a rounding
  artifact past an exact comparison).
- OPEN rounding intervals: a displayed value x with d decimals stands for
  (x − ½·10⁻ᵈ, x + ½·10⁻ᵈ). Endpoint contact proves nothing under an unknown
  rounding mode → UNRESOLVABLE, never a demotion.
- Every ambiguity — scientific notation, separators, unit mismatch or missing
  stated unit, denominator interval crossing zero, convention not locally
  explicit — returns UNRESOLVABLE. Only PROVED_COMPATIBLE may demote, and only
  from a demotion-capable resolver.

Statuses: PROVED_COMPATIBLE · DISCREPANCY_PERSISTS · UNRESOLVABLE.
"""
import re
from fractions import Fraction

COUNTERCHECK_VERSION = "2.0"

PROVED_COMPATIBLE = "PROVED_COMPATIBLE"
DISCREPANCY_PERSISTS = "DISCREPANCY_PERSISTS"
UNRESOLVABLE = "UNRESOLVABLE"

_SIMPLE_NUM = re.compile(r"^-?\d+(\.\d+)?$")
_RELATIVE_MARKER = re.compile(r"\brelative\b", re.I)


def decimals_of(raw):
    """Displayed decimal places of a plain numeral string; None when the string is
    not a simple decimal numeral (scientific notation, separators, '+5', '.5'...)."""
    raw = (raw or "").strip() if isinstance(raw, str) else None
    if not raw or not _SIMPLE_NUM.match(raw):
        return None
    return len(raw.split(".")[1]) if "." in raw else 0


def display_interval(raw):
    """Open interval (Fraction bounds) a displayed numeral stands for; None if
    unresolvable. Exact: Fraction('73.1') == 731/10."""
    d = decimals_of(raw)
    if d is None:
        return None
    x = Fraction(raw)
    half = Fraction(5, 10 ** (d + 1))
    return (x - half, x + half)


def _open_intervals_intersect(a, b):
    """Strict intersection of two open intervals; endpoint contact is False.
    Exact Fraction comparison — no precision to get wrong."""
    return max(a[0], b[0]) < min(a[1], b[1])


def _endpoint_contact(a, b):
    return max(a[0], b[0]) == min(a[1], b[1])


def delta_convention(stated_unit, stated_span, stated_raw):
    """Convention of a stated delta, decided by the UNIT first (a 'points' marker
    elsewhere in the sentence cannot re-type a % number — kills the
    'improves by 4.9% over five data points' misbinding):

    - stated unit 'point'  → points (new − old)
    - stated unit '%'      → relative ONLY if the word 'relative' appears LOCALLY
      (same clause, within a short window around the stated numeral);
      otherwise ambiguous → None
    - anything else        → None
    """
    if stated_unit == "point":
        return "points"
    if stated_unit != "%":
        return None
    span, raw = stated_span or "", (stated_raw or "").strip()
    i = span.find(raw)
    if not raw or i < 0:
        return None
    # clause-bounded local window around the numeral (mirrors the ledger's
    # local-metric binding idea)
    before = re.split(r"[,;:.]", span[max(0, i - 30):i])[-1]
    after = re.split(r"[,;:.]", span[i + len(raw): i + len(raw) + 30])[0]
    return "relative" if _RELATIVE_MARKER.search(before + " " + after) else None


def rounding_interval_delta(old_raw, new_raw, stated_raw, convention,
                            old_unit=None, new_unit=None, stated_unit=None):
    """HP-DELTA-ERROR resolver — REPORT-ONLY (see module doctrine): could true
    values inside the operands' display intervals produce a delta that displays
    as the stated value? Returns (status, evidence_dict). The evidence always
    carries certified: False — the old/new binding is model-assigned and the
    formula is not symmetric, so no outcome here may demote."""
    ev = {"resolver": "rounding_interval", "version": COUNTERCHECK_VERSION,
          "certified": False, "convention": convention,
          "inputs": {"old": old_raw, "new": new_raw, "stated": stated_raw}}
    if convention not in ("relative", "points"):
        return UNRESOLVABLE, dict(ev, why="convention not locally explicit for the stated value")
    if (old_unit or None) != (new_unit or None):
        return UNRESOLVABLE, dict(ev, why=f"operand units differ: {old_unit!r} vs {new_unit!r}")
    if convention == "relative" and stated_unit != "%":
        return UNRESOLVABLE, dict(ev, why="relative delta must be stated in %")
    if convention == "points" and stated_unit != "point":
        return UNRESOLVABLE, dict(ev, why="points delta must be stated in points")
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
    if _endpoint_contact(achievable, ist):
        return UNRESOLVABLE, dict(ev, why="endpoint contact — rounding mode unknown")
    return DISCREPANCY_PERSISTS, ev


def display_precision(a_raw, b_raw, a_unit=None, b_unit=None):
    """HP-NUM-INFLATE / HP-APPENDIX-CONTRA resolver — DEMOTION-CAPABLE: are two
    displays of the same quantity mutually consistent? True iff their open display
    intervals strictly intersect. The check is SYMMETRIC in its two arguments —
    the model-assigned fine/coarse roles cannot change the verdict, which is
    exactly why this resolver may demote. Returns (status, evidence_dict)."""
    ev = {"resolver": "display_precision", "version": COUNTERCHECK_VERSION,
          "certified": True,   # binding-invariant: symmetric in the two inputs
          "inputs": {"a": a_raw, "b": b_raw}}
    if (a_unit or None) != (b_unit or None):
        return UNRESOLVABLE, dict(ev, why=f"units differ: {a_unit!r} vs {b_unit!r}")
    ia, ib = display_interval(a_raw), display_interval(b_raw)
    if not (ia and ib):
        return UNRESOLVABLE, dict(ev, why="a value is not a plain decimal numeral")
    ev["a_interval"] = [str(ia[0]), str(ia[1])]
    ev["b_interval"] = [str(ib[0]), str(ib[1])]
    if _open_intervals_intersect(ia, ib):
        return PROVED_COMPATIBLE, ev
    if _endpoint_contact(ia, ib):
        return UNRESOLVABLE, dict(ev, why="endpoint contact — rounding mode unknown")
    return DISCREPANCY_PERSISTS, ev


# pattern_id -> (resolver, required numeric_basis roles, may_demote)
# may_demote is the binding-invariance verdict: display_precision is symmetric in
# its inputs (role swap cannot change the answer); the delta formula is not.
ALLOWLIST = {
    "HP-DELTA-ERROR": ("rounding_interval", frozenset({"old", "new", "stated"}), False),
    "HP-NUM-INFLATE": ("display_precision", frozenset({"fine", "coarse"}), True),
    "HP-APPENDIX-CONTRA": ("display_precision", frozenset({"fine", "coarse"}), True),
}
