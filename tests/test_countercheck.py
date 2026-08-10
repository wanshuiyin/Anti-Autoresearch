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
    from fractions import Fraction
    lo, hi = C.display_interval("78.0")
    assert lo == Fraction("77.95") and hi == Fraction("78.05")   # exact rationals


# ---- rounding_interval (HP-DELTA-ERROR) ----

def test_relative_delta_rounding_rescues_true_positive_case():
    # (78.0−73.1)/73.1·100 = 6.70…% — a stated "6.7% relative" is display-compatible;
    # NOTE: certified is False — this resolver reports, it never demotes
    st, ev = C.rounding_interval_delta("73.1", "78.0", "6.7", "relative", "%", "%", stated_unit="%")
    assert st == C.PROVED_COMPATIBLE, ev
    assert ev["certified"] is False


def test_relative_delta_real_error_persists():
    # true relative delta ≈ 6.7% — a stated "16.7% relative" cannot be rounding
    st, ev = C.rounding_interval_delta("73.1", "78.0", "16.7", "relative", "%", "%", stated_unit="%")
    assert st == C.DISCREPANCY_PERSISTS, ev


def test_points_delta_rounding():
    # 78.0 − 73.1 = 4.9 points; stated "5 points" (0 decimals) is display-compatible
    st, _ = C.rounding_interval_delta("73.1", "78.0", "5", "points", "%", "%", stated_unit="point")
    assert st == C.PROVED_COMPATIBLE
    # stated "6 points" is not
    st, _ = C.rounding_interval_delta("73.1", "78.0", "6", "points", "%", "%", stated_unit="point")
    assert st == C.DISCREPANCY_PERSISTS


def test_points_convention_requires_point_unit():
    # a % number cannot be a points delta, whatever the prose says
    st, ev = C.rounding_interval_delta("73.1", "78.0", "5", "points", "%", "%", stated_unit="%")
    assert st == C.UNRESOLVABLE and "points delta" in ev["why"]


def test_exact_arithmetic_no_precision_smuggling():
    # 20-digit operands (inside the length cap): exact Fractions must keep a real
    # discrepancy real — float or fixed-precision arithmetic would blur this to
    # "compatible"
    old = "9" * 18 + "00"
    new = "9" * 18 + "05"
    st, _ = C.rounding_interval_delta(old, new, "0.000000000000000001",
                                      "relative", None, None, stated_unit="%")
    assert st == C.DISCREPANCY_PERSISTS


def test_absurdly_long_numerals_unresolvable_not_crash():
    # a 5000-digit "numeral" must fail closed (UNRESOLVABLE), never demote or
    # trip Python's int-conversion limit
    big = "9" * 5000
    st, _ = C.rounding_interval_delta(big, big, "1", "relative", None, None, stated_unit="%")
    assert st == C.UNRESOLVABLE
    st, _ = C.display_precision(big, "78.0", a_unit="%", b_unit="%")
    assert st == C.UNRESOLVABLE


def test_exact_quantities_cannot_be_demoted():
    # λ=1 vs λ=1.4 (unitless hyperparameters) admit NO rounding interval — the
    # round-2 attack that wrongly demoted a real HP-APPENDIX-CONTRA critical
    st, ev = C.display_precision("1", "1.4", a_unit=None, b_unit=None)
    assert st == C.UNRESOLVABLE and "rounded measurement" in ev["why"]
    # and even a %/% PROVED_COMPATIBLE is certified: False (report-only)
    st, ev = C.display_precision("78.03", "78.0", a_unit="%", b_unit="%")
    assert st == C.PROVED_COMPATIBLE and ev["certified"] is False


def test_malformed_units_cannot_pass_as_equal():
    st, _ = C.display_precision("78.03", "78.0", a_unit=[], b_unit=[])
    assert st == C.UNRESOLVABLE


def test_duplicated_numeral_convention_ambiguous():
    assert C.delta_convention("%", "6.7% now vs 6.7% relative before", "6.7") is None


def test_no_explicit_convention_is_unresolvable():
    st, ev = C.rounding_interval_delta("73.1", "78.0", "6.7", None, "%", "%", stated_unit="%")
    assert st == C.UNRESOLVABLE and "convention" in ev["why"]


def test_unit_mismatch_unresolvable():
    st, _ = C.rounding_interval_delta("73.1", "78.0", "6.7", "relative", "%", "point", stated_unit="%")
    assert st == C.UNRESOLVABLE


def test_zero_crossing_denominator_unresolvable():
    st, ev = C.rounding_interval_delta("0.0", "78.0", "6.7", "relative", "%", "%", stated_unit="%")
    assert st == C.UNRESOLVABLE and "zero" in ev["why"]


def test_negative_operands_exact():
    # loss improves from -3.2 to -2.4: points delta 0.8, stated "0.8 points"
    st, _ = C.rounding_interval_delta("-3.2", "-2.4", "0.8", "points", None, None, stated_unit="point")
    assert st == C.PROVED_COMPATIBLE


def test_convention_unit_driven_and_local():
    # unit drives: a 'point'-unit number is points, whatever the prose
    assert C.delta_convention("point", "improves by 4.9 points", "4.9") == "points"
    # a % number is relative ONLY with a LOCAL 'relative' marker
    assert C.delta_convention("%", "a 6.7% relative improvement", "6.7") == "relative"
    assert C.delta_convention("%", "improves by 6.7%", "6.7") is None
    # the misbinding attack: 'points' elsewhere in the sentence can't re-type a % number
    assert C.delta_convention("%", "improves by 4.9% over five data points", "4.9") is None
    # 'relative' beyond the clause boundary does not bind
    assert C.delta_convention("%", "6.7% better. In relative terms, this is large", "6.7") is None


# ---- display_precision (HP-NUM-INFLATE / HP-APPENDIX-CONTRA) ----

def test_display_precision_compatible():
    # table 78.03 vs headline 78.0 — same quantity, coarser display
    st, _ = C.display_precision("78.03", "78.0", a_unit="%", b_unit="%")
    assert st == C.PROVED_COMPATIBLE


def test_display_precision_real_inflation_persists():
    # table 78.03 vs headline 79 — no rounding explains it
    st, _ = C.display_precision("78.03", "79", a_unit="%", b_unit="%")
    assert st == C.DISCREPANCY_PERSISTS


def test_display_precision_finer_midpoint_is_compatible():
    # 78.05 (2dp) genuinely CAN display as 78.1 at 1dp (e.g. true value 78.052):
    # the open intervals (78.045,78.055) and (78.05,78.15) strictly intersect
    st, _ = C.display_precision("78.05", "78.1", a_unit="%", b_unit="%")
    assert st == C.PROVED_COMPATIBLE


def test_display_precision_endpoint_contact_unresolvable():
    # 78.0 vs 78.1 at the same precision: their open intervals touch exactly at
    # 78.05 — whether that midpoint displays as 78.0 or 78.1 depends on the
    # rounding mode, so contact proves nothing and must NOT demote
    st, ev = C.display_precision("78.0", "78.1", a_unit="%", b_unit="%")
    assert C.display_precision("78.1", "78.0", a_unit="%", b_unit="%")[0] == st  # symmetric
    assert st == C.UNRESOLVABLE and "endpoint" in ev["why"]


def test_allowlist_shape_is_report_only():
    assert set(C.ALLOWLIST) == {"HP-DELTA-ERROR", "HP-NUM-INFLATE", "HP-APPENDIX-CONTRA"}
    # (resolver, required roles) — no demotion flag exists: resolvers are report-only.
    # rounding_interval fails binding-invariance; display_precision fails
    # rounding-provability ("exactly 50%" vs 50.4% is a real contradiction interval
    # logic would wrongly excuse).
    assert C.ALLOWLIST["HP-DELTA-ERROR"] == ("rounding_interval",
                                             frozenset({"old", "new", "stated"}))
    assert all(len(v) == 2 for v in C.ALLOWLIST.values())


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok {fn.__name__}")
    print(f"{len(fns)} passed")
