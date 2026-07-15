"""Run one market through all four de-vig methods and print a comparison.

    python examples/compare_methods.py
"""

from __future__ import annotations

from shin_devig import devig, implied_probs

# A 3-way soccer-style market: heavy favorite, coin-flip draw, longshot.
DECIMAL_ODDS = [1.40, 4.20, 9.00]
LABELS = ["Favorite", "Draw", "Longshot"]

METHODS = ["multiplicative", "additive", "power", "shin"]


def main() -> None:
    raw = implied_probs(DECIMAL_ODDS)
    overround = sum(raw) - 1.0

    print(f"Decimal odds: {DECIMAL_ODDS}")
    print(f"Raw implied probabilities: {[f'{p:.4f}' for p in raw]}")
    print(f"Overround (the vig): {overround:.4f} ({overround * 100:.2f}%)\n")

    header = f"{'Outcome':<10}" + "".join(f"{m:>16}" for m in METHODS)
    print(header)
    print("-" * len(header))

    results = {m: devig(DECIMAL_ODDS, method=m) for m in METHODS}
    for i, label in enumerate(LABELS):
        row = f"{label:<10}" + "".join(f"{results[m][i]:>16.4%}" for m in METHODS)
        print(row)

    print("-" * len(header))
    sums = "sum       " + "".join(f"{sum(results[m]):>16.4%}" for m in METHODS)
    print(sums)


if __name__ == "__main__":
    main()
