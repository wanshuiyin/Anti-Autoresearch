#!/usr/bin/env python3
"""
Unit tests for the deterministic counter-check resolvers (issue #15) — these lock
the ONLY path that may ever demote a critical. Invariants:

- open intervals: endpoint contact NEVER proves compatibility (rounding mode unknown);
- Decimal arithmetic (no binary-float artifacts);
- every ambiguity (convention not explicit, unit mismatch, zero-crossing denominator,
  non-plain numerals) is UNRESOLVABLE — a resolver that cannot DECIDE cannot demote.

Run: python3 tests/test_countercheck.py   (also pytest-compatible)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import countercheck as C  # noqa: E402


# ---- decimals / intervals ----

def test_decimals_of():
    assert C.decimals_of("78.0") == 1
    assert C.decimals_of("78") == 0
    assert C.decimals_of("-3.25") == 2
    assert C.decimals_of("1e3") is None          # scientific → unresolvable
    assert C.decimals_of("1,000") is None        # separators → unresolvable
    assert C.decimals_of("") is None


def test_display_interval_open():
    lo, hi = C.display_interval("78.0")
    assert str(lo) == "77.95" and str(hi) == "78.05"


# ---- rounding_interval (HP-DELTA-ERROR) ----

def test_relative_delta_rounding_rescues_true_positive_case():
    # (78.0−73.1)/73.1·100 = 6.70…% — a stated "6.7% relative" is display-compatible
    st, ev = C.rounding_interval_delta("73.1", "78.0", "6.7", "relative", "%", "%")
    assert st == C.PROVED_COMPATIBLE, ev


def test_relative_delta_real_error_persists():
    # true relative delta ≈ 6.7% — a stated "16.7% relative" cannot be rounding
    st, ev = C.rounding_interval_delta("73.1", "78.0", "16.7", "relative", "%", "%")
    assert st == C.DISCREPANCY_PERSISTS, ev


def test_points_delta_rounding():
    # 78.0 − 73.1 = 4.9 points; stated "5 points" (0 decimals) is display-compatible
    st, _ = C.rounding_interval_delta("73.1", "78.0", "5", "points", "%", "%")
    assert st == C.PROVED_COMPATIBLE
    # stated "6 points" is not
    st, _ = C.rounding_interval_delta("73.1", "78.0", "6", "points", "%", "%")
    assert st == C.DISCREPANCY_PERSISTS


def test_no_explicit_convention_is_unresolvable():
    st, ev = C.rounding_interval_delta("73.1", "78.0", "6.7", None, "%", "%")
    assert st == C.UNRESOLVABLE and "convention" in ev["why"]


def test_unit_mismatch_unresolvable():
    st, _ = C.rounding_interval_delta("73.1", "78.0", "6.7", "relative", "%", "point")
    assert st == C.UNRESOLVABLE


def test_zero_crossing_denominator_unresolvable():
    st, ev = C.rounding_interval_delta("0.0", "78.0", "6.7", "relative", "%", "%")
    assert st == C.UNRESOLVABLE and "zero" in ev["why"]


def test_convention_grammar():
    assert C.delta_convention_from_span("improves by 4.9 points over the baseline") == "points"
    assert C.delta_convention_from_span("a 6.7% relative improvement") == "relative"
    assert C.delta_convention_from_span("improves by 6.7%") is None          # ambiguous
    assert C.delta_convention_from_span("relative gain of 5 points") is None  # both markers


# ---- display_precision (HP-NUM-INFLATE / HP-APPENDIX-CONTRA) ----

def test_display_precision_compatible():
    # table 78.03 vs headline 78.0 — same quantity, coarser display
    st, _ = C.display_precision("78.03", "78.0", "%", "%")
    assert st == C.PROVED_COMPATIBLE


def test_display_precision_real_inflation_persists():
    # table 78.03 vs headline 79 — no rounding explains it
    st, _ = C.display_precision("78.03", "79", "%", "%")
    assert st == C.DISCREPANCY_PERSISTS


def test_display_precision_finer_midpoint_is_compatible():
    # 78.05 (2dp) genuinely CAN display as 78.1 at 1dp (e.g. true value 78.052):
    # the open intervals (78.045,78.055) and (78.05,78.15) strictly intersect
    st, _ = C.display_precision("78.05", "78.1", "%", "%")
    assert st == C.PROVED_COMPATIBLE


def test_display_precision_endpoint_contact_unresolvable():
    # 78.0 vs 78.1 at the same precision: their open intervals touch exactly at
    # 78.05 — whether that midpoint displays as 78.0 or 78.1 depends on the
    # rounding mode, so contact proves nothing and must NOT demote
    st, ev = C.display_precision("78.0", "78.1", "%", "%")
    assert st == C.UNRESOLVABLE and "endpoint" in ev["why"]


def test_allowlist_shape():
    assert set(C.ALLOWLIST) == {"HP-DELTA-ERROR", "HP-NUM-INFLATE", "HP-APPENDIX-CONTRA"}
    assert C.ALLOWLIST["HP-DELTA-ERROR"][1] == frozenset({"old", "new", "stated"})


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok {fn.__name__}")
    print(f"{len(fns)} passed")
