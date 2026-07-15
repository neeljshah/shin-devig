"""De-vig methods: convert bookmaker decimal odds into fair probabilities.

A sportsbook's quoted odds always imply probabilities that sum to MORE than
1.0 -- the excess (the "overround" or "vig") is the book's built-in margin.
Naively using 1/decimal_odds as "the probability" overstates every outcome
by roughly the same amount. De-vigging removes that margin; the four
methods below differ in *how* they distribute the correction across
outcomes, which matters most on lines with a strong favorite and a
longshot (the "favorite-longshot bias" -- longshots are historically
over-bet relative to favorites, so a proportional split misprices both).

Methods:
  multiplicative -- proportional renormalization: p_i / sum(p_i). The
                    baseline. Splits the vig proportionally to each
                    outcome's implied probability; assumes the market is
                    symmetrically wrong about favorites vs. longshots.
  additive       -- subtract the overround, split equally, in probability
                    space: p_i - (S-1)/n. A flat percentage-point shave
                    per outcome, blind to each outcome's odds.
  power          -- solve for exponent k such that sum(p_i ** k) == 1 and
                    return p_i ** k. With overround present, k > 1, which
                    shrinks small probabilities proportionally more than
                    large ones: relative to `multiplicative` it moves vig
                    off the favorite and onto the longshot -- a numerical
                    correction for the favorite-longshot bias.
  shin           -- Shin (1992) insider-trading model. Assumes a fraction z
                    of bettors are informed and the book prices against
                    that risk by loading extra margin onto longshots (to
                    cap losses if an informed bettor hits a longshot).
                    Solves for z via bisection, then reconstructs
                    probabilities consistent with it. Like `power`, it
                    reallocates vig toward the longshot relative to
                    `multiplicative`, but derives the reallocation from an
                    economic model rather than a functional form.

All four take and return probabilities that sum to 1.0 within numerical
tolerance. Use `implied_probs` to convert from decimal odds first, or call
`devig` directly on decimal odds.

References:
  Shin, H.S. (1992). "Prices of State Contingent Claims with Insider
  Traders, and the Favourite-Longshot Bias." The Economic Journal, 102(411).
  Strumbelj, E. (2014). "On determining probability forecasts from betting
  odds." International Journal of Forecasting, 30(4).
"""

from __future__ import annotations

import math
from typing import Sequence


def _validate_odds(odds: Sequence[float]) -> list[float]:
    odds = list(odds)
    if len(odds) < 2:
        raise ValueError(f"need at least 2 outcomes, got {len(odds)}")
    for o in odds:
        if not math.isfinite(o) or o <= 1.0:
            raise ValueError(
                f"decimal odds must be finite and > 1.0, got {o!r}"
            )
    return [float(o) for o in odds]


def implied_probs(odds: Sequence[float]) -> list[float]:
    """Decimal odds -> raw (still vigged) implied probabilities."""
    odds = _validate_odds(odds)
    return [1.0 / o for o in odds]


def _renormalize(values: Sequence[float]) -> list[float]:
    total = sum(values)
    if total <= 0:
        n = len(values)
        return [1.0 / n] * n
    return [v / total for v in values]


def multiplicative_devig(probs: Sequence[float]) -> list[float]:
    """Proportional renormalization: p_i / sum(p_i). The baseline method."""
    return _renormalize([float(p) for p in probs])


def additive_devig(probs: Sequence[float]) -> list[float]:
    """Subtract the overround equally, in probability space.

    p_i' = p_i - (S - 1) / n, clipped at a small epsilon and renormalized
    so the result always sums exactly to 1 even if a longshot's share of
    the overround would otherwise push it negative.
    """
    probs = [float(p) for p in probs]
    n = len(probs)
    s = sum(probs)
    share = (s - 1.0) / n
    out = [max(p - share, 1e-9) for p in probs]
    return _renormalize(out)


def power_devig(
    probs: Sequence[float], *, max_iter: int = 200, tol: float = 1e-12
) -> list[float]:
    """Power method: bisect for k such that sum(p_i ** k) == 1.

    total(k) = sum(p_i ** k) is strictly decreasing in k for p_i in (0, 1),
    so bisection on a bracket with total(lo) > 1 > total(hi) converges
    monotonically to double precision within the iteration budget. With
    overround present the solved k is > 1, which shrinks longshot
    probabilities proportionally more than favorites'.
    """
    probs = [float(p) for p in probs]
    if any(p <= 0 for p in probs):
        return multiplicative_devig(probs)
    s = sum(probs)
    if s <= 1.0 + 1e-12:
        return multiplicative_devig(probs)  # no vig to remove

    def total(k: float) -> float:
        return sum(p ** k for p in probs)

    lo, hi = 0.5, 8.0
    if total(lo) < 1.0:
        lo = 0.01
    if total(hi) > 1.0:
        hi = 32.0

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if total(mid) > 1.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break

    k = 0.5 * (lo + hi)
    return _renormalize([p ** k for p in probs])


def _shin_prob_at_z(z: float, q: float, s: float) -> float:
    """Shin (1992) formula for a single outcome at a given z. Not exported."""
    return (math.sqrt(z * z + 4.0 * (1.0 - z) * q * q / s) - z) / (2.0 * (1.0 - z))


def shin_devig(
    probs: Sequence[float], *, max_iter: int = 64, tol: float = 1e-12
) -> list[float]:
    """Shin (1992) devig via bisection on z in [0, 1).

    Solves for the informed-trader fraction z such that

        p_i(z) = (sqrt(z^2 + 4(1-z) q_i^2 / S) - z) / (2(1 - z))

    sums to 1, where q_i are the raw vigged probabilities and S = sum(q_i).
    The bracket is well-behaved: sum_i p_i(z) is monotonically decreasing
    in z over [0, 1), so it converges to double precision in <= 64 steps
    (bisection halves the [0, 1) interval; 2**-64 is below float epsilon).
    At z = 0 the formula reduces to q_i / sqrt(S), which renormalizes to
    q_i / S -- exactly the multiplicative (proportional) devig.
    Falls back to `multiplicative_devig` if there is no overround.
    """
    probs = [float(p) for p in probs]
    s = sum(probs)
    if s <= 1.0 + 1e-12 or any(p <= 0 for p in probs):
        return multiplicative_devig(probs)

    def sum_p(z: float) -> float:
        return sum(_shin_prob_at_z(z, q, s) for q in probs)

    lo, hi = 0.0, 1.0 - 1e-9
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if sum_p(mid) > 1.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break

    z = 0.5 * (lo + hi)
    return _renormalize([_shin_prob_at_z(z, q, s) for q in probs])


_METHODS = {
    "multiplicative": multiplicative_devig,
    "proportional": multiplicative_devig,
    "additive": additive_devig,
    "power": power_devig,
    "shin": shin_devig,
}


def devig(odds: Sequence[float], method: str = "shin") -> list[float]:
    """De-vig a market of 2+ decimal odds. Returns probabilities summing to 1.

    method: one of "multiplicative", "additive", "power", "shin" (default).
    "proportional" is accepted as an alias for "multiplicative".
    """
    key = (method or "shin").lower()
    if key not in _METHODS:
        raise ValueError(
            f"unknown devig method '{method}'. Expected one of: {sorted(_METHODS)}"
        )
    probs = implied_probs(odds)
    return _METHODS[key](probs)


__all__ = [
    "implied_probs",
    "multiplicative_devig",
    "additive_devig",
    "power_devig",
    "shin_devig",
    "devig",
]
