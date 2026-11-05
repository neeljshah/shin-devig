# shin-devig

Convert decimal sportsbook odds into probability estimates with multiplicative,
additive, power and Shin (1992) de-vig methods. The library makes margin removal
explicit so forecasts can be compared with a consistent market-probability
baseline.

Pure Python, with no runtime dependencies. Removing margin does not establish
that a probability estimate is calibrated or that a model outperforms the market.

## Install

Requires Python 3.10 or later. From a terminal:

```bash
git clone https://github.com/neeljshah/shin-devig.git
cd shin-devig
python -m pip install -e ".[dev]"
```

The `dev` extra installs pytest; use `python -m pip install -e .` for the library
alone.

## Runnable example

```bash
python examples/compare_methods.py
```

Output:

```text
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

The example is a synthetic three-outcome market. Its percentages describe
normalized probabilities, not measured forecasting performance.

## Python API

```python
from shin_devig import devig, implied_probs

odds = [1.40, 4.20, 9.00]
raw = implied_probs(odds)
probabilities = devig(odds, method="shin")
print([round(p, 4) for p in probabilities])
```

```text
[0.6876, 0.2185, 0.094]
```

`devig` accepts at least two finite decimal odds greater than 1.0. Invalid odds
or an unknown method raise `ValueError`. The default method is `shin`;
`proportional` is an alias for `multiplicative`.

| Method | Calculation |
| --- | --- |
| `multiplicative` | Divide each raw implied probability by their sum. |
| `additive` | Subtract an equal share of the overround, clip at a small positive value and normalize. |
| `power` | Use bisection to solve for an exponent, then normalize. |
| `shin` | Use bisection for the Shin informed-trader parameter, then normalize. |

Power and Shin fall back to multiplicative normalization when the implied
probabilities sum to at most one, within numerical tolerance. The formulas make
different assumptions about how margin is distributed; choosing among them
requires evaluation against observed outcomes.

## Tests

```bash
python -m pytest tests/test_methods.py -q
```

The 26 tests check normalization, outcome ordering, symmetric and no-margin
markets, method identities, the worked three-outcome market and invalid input.
GitHub Actions runs this test file on each push and pull request.

## Context

[The CourtVision evidence site](https://neeljshah.github.io/court-vision/)
contains the forecasting results and public retraction record. Its moneyline
models land near the devigged close without beating it; totals and tennis trail.

## Reference

Shin, H.S. (1992). "Prices of State Contingent Claims with Insider Traders,
and the Favourite-Longshot Bias." *The Economic Journal*, 102(411), 426-435.

## License

[MIT](LICENSE), copyright Neel Shah 2026.
