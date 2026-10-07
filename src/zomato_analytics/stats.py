"""Hypothesis tests behind the headline claims.

Ratings are bounded, ordinal-ish and skewed, so non-parametric tests are used
throughout, and every p-value is reported with an effect size: with ~9,500 rows
almost any difference is "significant", so the business question is whether it
is *large enough to matter*.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .config import DEFAULT_CONFIG, AnalysisConfig


def _magnitude(value: float, small: float, medium: float, large: float) -> str:
    a = abs(value)
    if a >= large:
        return "large"
    if a >= medium:
        return "medium"
    if a >= small:
        return "small"
    return "negligible"


def compare_groups(
    df: pd.DataFrame,
    flag: str,
    metric: str = "aggregate_rating",
    label: str | None = None,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> dict:
    """Mann-Whitney U with rank-biserial correlation as the effect size."""
    rated = df[df["is_rated"]]
    a = rated.loc[rated[flag].astype(bool), metric].dropna().astype(float)
    b = rated.loc[~rated[flag].astype(bool), metric].dropna().astype(float)
    if len(a) < 2 or len(b) < 2:
        return {
            "test": f"{label or flag}",
            "method": "Mann-Whitney U",
            "n": len(a) + len(b),
            "statistic": np.nan,
            "p_value": np.nan,
            "effect_size": np.nan,
            "effect_magnitude": "insufficient data",
            "significant": False,
            "interpretation": "Not enough data in one of the groups.",
        }
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    rbc = 1 - 2 * u / (len(a) * len(b))  # >0 means group b tends higher
    rbc = -rbc  # make positive mean "with feature" is higher
    mag = _magnitude(rbc, 0.1, 0.3, 0.5)
    sig = bool(p < cfg.alpha)
    direction = "higher" if a.median() >= b.median() else "lower"
    return {
        "test": label or flag,
        "method": "Mann-Whitney U",
        "n": int(len(a) + len(b)),
        "statistic": float(u),
        "p_value": float(p),
        "effect_size": round(float(rbc), 3),
        "effect_magnitude": mag,
        "significant": sig,
        "interpretation": (
            f"Restaurants with {label or flag} rate {direction} "
            f"(median {a.median():.2f} vs {b.median():.2f}); "
            f"{'statistically significant' if sig else 'not significant'}, {mag} effect."
        ),
    }


def correlation(
    df: pd.DataFrame, x: str, y: str, label: str, cfg: AnalysisConfig = DEFAULT_CONFIG
) -> dict:
    d = df[df["is_rated"]][[x, y]].dropna().astype(float)
    rho, p = stats.spearmanr(d[x], d[y])
    mag = _magnitude(rho, 0.1, 0.3, 0.5)
    sig = bool(p < cfg.alpha)
    return {
        "test": label,
        "method": "Spearman rank correlation",
        "n": int(len(d)),
        "statistic": round(float(rho), 3),
        "p_value": float(p),
        "effect_size": round(float(rho), 3),
        "effect_magnitude": mag,
        "significant": sig,
        "interpretation": f"{'Positive' if rho > 0 else 'Negative'} {mag} monotonic association "
        f"(rho={rho:.2f}); {'significant' if sig else 'not significant'}.",
    }


def price_band_test(df: pd.DataFrame, cfg: AnalysisConfig = DEFAULT_CONFIG) -> dict:
    """Kruskal-Wallis across price bands with epsilon-squared effect size."""
    rated = df[df["is_rated"]]
    groups = [
        g["aggregate_rating"].astype(float).to_numpy()
        for _, g in rated.groupby("price_range")
        if len(g) >= 2
    ]
    h, p = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    eps2 = h / ((n**2 - 1) / (n + 1))
    mag = _magnitude(eps2, 0.01, 0.08, 0.26)
    sig = bool(p < cfg.alpha)
    return {
        "test": "rating differs by price band",
        "method": "Kruskal-Wallis H",
        "n": int(n),
        "statistic": round(float(h), 2),
        "p_value": float(p),
        "effect_size": round(float(eps2), 3),
        "effect_magnitude": mag,
        "significant": sig,
        "interpretation": f"Ratings {'do' if sig else 'do not'} differ across price bands; "
        f"{mag} effect (epsilon^2={eps2:.3f}).",
    }


def run_all(df: pd.DataFrame, cfg: AnalysisConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """All tests, overall and restricted to India (to remove the country mix effect)."""
    results = []
    for scope, data in (("All markets", df), ("India only", df[df["country"] == "India"])):
        if data["is_rated"].sum() < 20:
            continue
        tests = [
            compare_groups(data, "has_online_delivery", label="online delivery", cfg=cfg),
            compare_groups(data, "has_table_booking", label="table booking", cfg=cfg),
            price_band_test(data, cfg),
            correlation(data, "cost_for_two_gbp", "aggregate_rating", "cost vs rating", cfg),
            correlation(data, "log_votes", "aggregate_rating", "engagement (votes) vs rating", cfg),
        ]
        for t in tests:
            t["scope"] = scope
        results.extend(tests)
    out = pd.DataFrame(results)
    cols = [
        "scope",
        "test",
        "method",
        "n",
        "statistic",
        "p_value",
        "effect_size",
        "effect_magnitude",
        "significant",
        "interpretation",
    ]
    return out[cols]
