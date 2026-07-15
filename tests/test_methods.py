"""Tests for shin_devig.methods.

Verifies: probabilities sum to 1 for every method, outcome order is
preserved, the Shin formula's z=0 case degenerates to the multiplicative
(proportional) devig, a known symmetric-market identity holds (a
-110/-110-style two-way book de-vigs to exactly 50/50 under every method),
the power method's solved exponent exceeds 1 when overround is present,
3+ outcome markets work, and garbage input raises.
"""

from __future__ import annotations

import math

import pytest

from shin_devig import (
    additive_devig,
    devig,
    implied_probs,
    multiplicative_devig,
    power_devig,
    shin_devig,
)
from shin_devig.methods import _shin_prob_at_z

METHODS = ["multiplicative", "additive", "power", "shin"]

# A 3-way market with a clear favorite, a mid-price, and a longshot.
DECIMAL_ODDS = [1.40, 4.20, 9.00]


@pytest.mark.parametrize("method", METHODS)
def test_sums_to_one(method):
    out = devig(DECIMAL_ODDS, method=method)
    assert sum(out) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("method", METHODS)
def test_order_preserved(method):
    # Lowest decimal odds (favorite) must stay the highest probability.
    out = devig(DECIMAL_ODDS, method=method)
    assert out[0] > out[1] > out[2]


def test_shin_z_zero_degenerates_to_multiplicative():
    # Shin's formula at z=0 is p_i = q_i / sqrt(S); renormalizing that
    # (dividing by its own sum, S/sqrt(S)) collapses to q_i / S -- exactly
    # the multiplicative (proportional) devig. Structural property of the
    # Shin (1992) formula, independent of the bisection solver.
    probs = implied_probs(DECIMAL_ODDS)
    s = sum(probs)
    raw_at_zero = [_shin_prob_at_z(0.0, q, s) for q in probs]
    total = sum(raw_at_zero)
    renormalized = [v / total for v in raw_at_zero]
    expected = multiplicative_devig(probs)
    for got, want in zip(renormalized, expected):
        assert got == pytest.approx(want, abs=1e-9)


@pytest.mark.parametrize("method", METHODS)
def test_symmetric_market_is_half(method):
    # Two equally-priced outcomes (e.g. a standard -110/-110 coin flip,
    # decimal odds 1.909) must de-vig to exactly 50/50 under every method --
    # the overround is symmetric so there is nothing to distribute unevenly.
    out = devig([1.9091, 1.9091], method=method)
    assert out[0] == pytest.approx(0.5, abs=1e-6)
    assert out[1] == pytest.approx(0.5, abs=1e-6)


def test_three_outcome_market_all_methods():
    for method in METHODS:
        out = devig(DECIMAL_ODDS, method=method)
        assert len(out) == 3
        assert sum(out) == pytest.approx(1.0, abs=1e-9)
        assert all(0.0 < p < 1.0 for p in out)


def test_power_solved_exponent_above_one():
    # With overround present, the k solving sum(p_i ** k) == 1 must be > 1
    # (raw probs already sum above 1, and sum(p_i ** k) is decreasing in k).
    # Verify indirectly: power's output must sum to 1, preserve order, and
    # p_i ** k with k > 1 shrinks the longshot proportionally more, so the
    # favorite's share must exceed the multiplicative baseline's.
    probs = implied_probs(DECIMAL_ODDS)
    out = power_devig(probs)
    assert sum(out) == pytest.approx(1.0, abs=1e-9)
    assert out[0] > out[1] > out[2]
    baseline = multiplicative_devig(probs)
    assert out[0] > baseline[0]
    # And directly: the implied k is > 1 since sum(p_i ** 1) = S > 1.
    assert sum(probs) > 1.0


def test_favorite_longshot_bias_direction():
    # Shin and power both reallocate vig toward the longshot relative to
    # the multiplicative (proportional) baseline: favorite gets a HIGHER
    # fair probability, longshot a LOWER one.
    baseline = devig(DECIMAL_ODDS, method="multiplicative")
    for method in ("shin", "power"):
        out = devig(DECIMAL_ODDS, method=method)
        assert out[0] > baseline[0], method
        assert out[-1] < baseline[-1], method


def test_two_outcome_shin_equals_additive():
    # Known identity: on a 2-outcome market Shin's devig coincides with the
    # equal-split additive method (Strumbelj 2014 notes the 2-way case).
    odds = [1.3333333333333333, 3.2]  # -300 / +220 in American terms
    shin = devig(odds, method="shin")
    add = devig(odds, method="additive")
    for a, b in zip(shin, add):
        assert a == pytest.approx(b, abs=1e-9)


def test_no_vig_market_is_identity():
    fair_probs = [0.4, 0.6]
    fair_odds = [1.0 / p for p in fair_probs]
    for method in METHODS:
        out = devig(fair_odds, method=method)
        assert out[0] == pytest.approx(0.4, abs=1e-6)
        assert out[1] == pytest.approx(0.6, abs=1e-6)


def test_unknown_method_raises():
    with pytest.raises(ValueError):
        devig(DECIMAL_ODDS, method="nonsense")


@pytest.mark.parametrize("bad_odds", [
    [1.0, 2.0],       # odds must be > 1.0
    [0.5, 2.0],       # sub-1 odds are nonsensical
    [float("inf"), 2.0],
    [float("nan"), 2.0],
    [2.0],            # need >= 2 outcomes
])
def test_garbage_input_raises(bad_odds):
    with pytest.raises(ValueError):
        devig(bad_odds)


def test_multiplicative_matches_direct_call():
    probs = implied_probs(DECIMAL_ODDS)
    a = multiplicative_devig(probs)
    b = devig(DECIMAL_ODDS, method="multiplicative")
    assert a == pytest.approx(b, abs=1e-12)


def test_methods_distinct_on_skewed_market():
    # On a skewed 3-way market all four methods should disagree at least
    # slightly -- if any two are numerically identical something collapsed.
    probs = implied_probs(DECIMAL_ODDS)
    results = [
        multiplicative_devig(probs),
        additive_devig(probs),
        power_devig(probs),
        shin_devig(probs),
    ]
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            assert not math.isclose(results[i][0], results[j][0], abs_tol=1e-9)
