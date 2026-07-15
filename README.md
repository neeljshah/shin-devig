# shin-devig

De-vig sportsbook odds into fair probabilities using four methods, including
the Shin (1992) insider-trading model. Pure Python, zero dependencies.

This is a probability-measurement library, not a betting tool. It answers
"what does the market actually think the true probability is, once the
bookmaker's margin is stripped out?" -- it makes no claim about whether that
probability is exploitable, and includes no staking, ROI, or edge logic.

```python
from shin_devig import devig

decimal_odds = [1.40, 4.20, 9.00]   # favorite / mid / longshot
devig(decimal_odds, method="shin")
# -> [0.6876, 0.2185, 0.0940]  (sums to 1.0)
```

## Why raw implied probability is wrong

Every decimal odds quote implies a probability: `p = 1 / odds`. Sum the
implied probabilities across all outcomes in a market and you'll get a
number bigger than 1.0 -- often 1.02-1.10 for a liquid two-way market, more
for exotic or thin ones. That excess is the **overround** (the "vig" or
"juice"): the bookmaker's structural margin, built into the price before a
single bet is placed.

Treating `1 / odds` as "the probability" therefore overstates every
outcome by roughly its share of the overround. **De-vigging** removes that
margin so the remaining numbers form a genuine probability distribution
(sum to exactly 1.0). The question this library answers is *how* to
distribute the correction across outcomes -- and that choice matters a lot
whenever a market has a big favorite and a big longshot, because of the
well-documented **favorite-longshot bias**: bettors have historically
overbet longshots and underbet favorites relative to true probability, so a
proportional correction misprices both ends of the market.

## The four methods

**`multiplicative`** -- proportional renormalization: divide each raw
implied probability by their sum, `p_i / S`. The baseline everyone starts
with (also called "proportional" or "normalization"; accepted here under
either name). It splits the vig proportionally to each outcome's implied
probability, which implicitly assumes the market is *symmetrically* wrong
about favorites and longshots. On favorite-longshot markets that assumption
is empirically false -- but as a one-line, assumption-light default it is
the right reference point every other method is measured against.

**`additive`** -- subtract the overround, split equally, in probability
space: `p_i - (S - 1) / n`, where `n` is the outcome count. A flat
percentage-point shave off every outcome, blind to each outcome's odds. A
2-point shave is tiny relative to a 90% favorite and enormous relative to a
5% longshot, so relative to `multiplicative` this method takes *more* of
the vig out of the longshot -- crudely pointing the same direction as Shin,
but by accident of arithmetic rather than by any model. It can also drive a
very long longshot's probability negative (clipped and renormalized here).

**`power`** -- solve (by bisection) for a single exponent `k` such that
`sum(p_i ** k) == 1`, then return `p_i ** k`. With overround present the
solved `k` is greater than 1, and raising probabilities in (0, 1) to a
power above 1 shrinks small values proportionally more than large ones: the
longshot gives up more of the vig than the favorite does. So `power` is a
favorite-longshot-aware correction expressed as a functional form -- more
principled than `additive`'s flat shave, and it scales correctly with the
size of the overround because `k` is fit to the market rather than fixed.

**`shin`** -- the Shin (1992) insider-trading model. Shin assumes a fraction
`z` of the market's money comes from informed traders, and that the
bookmaker prices defensively against that risk by loading extra margin onto
the longshot (a cap on losses if an informed bettor happens to hit a big
price). Solving for `z` by bisection and reconstructing probabilities from
it recovers a correction that -- like `power` -- pulls probability mass
*from* the longshot *back to* the favorite relative to the `multiplicative`
baseline. The difference is *why*: Shin derives the reallocation from an
economic model of informed trading, not from a functional form. It is the
standard choice wherever a market has a real favorite-longshot skew --
horse racing, MMA, boxing, lopsided team-sport lines -- and the estimated
`z` is itself interpretable as the market's implied informed-money
fraction. At `z = 0` (no informed money) the Shin formula degenerates
exactly to the `multiplicative` baseline.

## Worked example

A 3-way market (e.g. a soccer 1X2 line) with decimal odds `[1.40, 4.20,
9.00]` for favorite / draw / longshot:

```
$ python examples/compare_methods.py
Decimal odds: [1.4, 4.2, 9.0]
Raw implied probabilities: ['0.7143', '0.2381', '0.1111']
Overround (the vig): 0.0635 (6.35%)

Outcome     multiplicative        additive           power            shin
--------------------------------------------------------------------------
Favorite          67.1642%        69.3122%        69.5067%        68.7556%
Draw              22.3881%        21.6931%        21.1949%        21.8477%
Longshot          10.4478%         8.9947%         9.2984%         9.3968%
--------------------------------------------------------------------------
sum              100.0000%       100.0000%       100.0000%       100.0000%
```

Read the favorite's row left to right: the `multiplicative` baseline gives
it 67.16%, and every other method gives it *more* -- `shin` 68.76%,
`additive` 69.31%, `power` 69.51% -- by shifting vig share away from the
longshot (10.45% baseline down to 8.99-9.40%). That is the
favorite-longshot correction in action: **`shin` and `power` both
reallocate vig toward the longshot relative to `multiplicative`**, `power`
via its solved exponent, `shin` via its informed-trading model (and
`additive`'s flat shave lands in the same territory on this market by
arithmetic accident). Which method is closest to the *true* probability is
an empirical question -- Strumbelj (2014) finds Shin and power-type
corrections beat plain normalization on average -- not something any
formula proves on its own for a single market.

One known identity worth noting: on a **two-outcome** market, `shin` and
`additive` coincide exactly (verified in
`tests/test_methods.py::test_two_outcome_shin_equals_additive`, and
stress-tested numerically to ~1e-15 over random 2-way markets). The
methods only genuinely fan out on markets with three or more outcomes.

## Installation

```bash
pip install -e .
```

Zero runtime dependencies -- pure standard-library Python (`math`).

## Usage

```python
from shin_devig import devig, implied_probs

odds = [1.40, 4.20, 9.00]
implied_probs(odds)                    # -> raw, still-vigged probabilities
devig(odds, method="shin")             # -> fair probabilities, sums to 1.0
devig(odds, method="multiplicative")   # alias: "proportional"
devig(odds, method="additive")
devig(odds, method="power")
```

`devig` validates its input: decimal odds must be finite and strictly
greater than 1.0, and a market needs at least two outcomes. Garbage input
raises `ValueError` rather than silently returning nonsense.

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

## References

- Shin, H.S. (1992). "Prices of State Contingent Claims with Insider
  Traders, and the Favourite-Longshot Bias." *The Economic Journal*,
  102(411), 426-435.
- Strumbelj, E. (2014). "On determining probability forecasts from betting
  odds." *International Journal of Forecasting*, 30(4), 934-943. (Reviews
  and compares devig methods, including Shin's, against realized outcomes.)
- The favorite-longshot bias itself -- the empirical tendency for market
  prices to overstate longshot probability and understate favorite
  probability -- is one of the oldest documented anomalies in betting
  markets and a recurring case study in the "wisdom of crowds" literature
  on when aggregated bettor beliefs are (and aren't) well-calibrated.

## License

MIT. See `LICENSE`.

## Author

Neel Shah -- [neeljshah22@gmail.com](mailto:neeljshah22@gmail.com) --
[github.com/neeljshah](https://github.com/neeljshah)

Distilled out of a larger multi-sport forecasting system as a standalone,
single-purpose library.
