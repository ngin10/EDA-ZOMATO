"""Deterministic synthetic data with the same schema and quirks as the Kaggle file.

The real ``zomato.csv`` is distributed under Kaggle's terms and is not committed to
this repository. This generator lets the pipeline, tests and CI run end-to-end
without it. It deliberately reproduces the source file's known defects (0.0
sentinel ratings, mislabelled currencies, (0,0) coordinates, duplicates, garbled
text, extreme prices) so that the cleaning code is exercised for real.

Numbers produced from this data are illustrative only and must not be quoted as
findings.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import io
from .schema import RAW_COLUMNS

# country_code -> (weight, raw currency label, cities)
_MARKETS: dict[int, tuple[float, str, list[str]]] = {
    1: (
        0.80,
        "Indian Rupees(Rs.)",
        [
            "New Delhi",
            "Gurgaon",
            "Noida",
            "Faridabad",
            "Bangalore",
            "Mumbai",
            "Pune",
            "Kolkata",
            "Chennai",
            "Hyderabad",
        ],
    ),
    216: (0.06, "Dollar($)", ["Orlando", "Tampa Bay", "Atlanta", "Des Moines", "Pensacola"]),
    215: (0.04, "Pounds(£)", ["London", "Manchester", "Edinburgh", "Birmingham"]),
    214: (0.012, "Emirati Diram(AED)", ["Dubai", "Abu Dhabi", "Sharjah"]),
    30: (0.012, "Brazilian Real(R$)", ["Rio de Janeiro", "SÃ£o Paulo", "BrasÃ­lia"]),
    189: (0.012, "Rand(R)", ["Cape Town", "Johannesburg", "Pretoria"]),
    148: (0.008, "NewZealand($)", ["Auckland", "Wellington City"]),
    208: (0.008, "Turkish Lira(TL)", ["ÛÁstanbul", "Ankara"]),
    14: (0.006, "Dollar($)", ["Sydney", "Melbourne"]),
    162: (0.005, "Botswana Pula(P)", ["Makati City", "Pasig City", "Taguig City"]),
    94: (0.005, "Indonesian Rupiah(IDR)", ["Jakarta", "Bogor"]),
    166: (0.005, "Qatari Rial(QR)", ["Doha"]),
    184: (0.005, "Dollar($)", ["Singapore"]),
    191: (0.005, "Sri Lankan Rupee(LKR)", ["Colombo"]),
    37: (0.002, "Dollar($)", ["Toronto", "Vancouver"]),
}

_CUISINES = [
    "North Indian",
    "Chinese",
    "Fast Food",
    "Mughlai",
    "Italian",
    "Bakery",
    "Cafe",
    "Continental",
    "Desserts",
    "South Indian",
    "Street Food",
    "Pizza",
    "American",
    "Burger",
    "Seafood",
    "Japanese",
    "Thai",
    "Mexican",
    "British",
    "Mediterranean",
    "Healthy Food",
    "Asian",
    "Beverages",
    "Indian",
]

# Typical GBP cost for two by price range (median of a log-normal).
_GBP_COST_BY_PRICE = {1: 6.0, 2: 14.0, 3: 30.0, 4: 60.0}


def _rating_text_color(r: float) -> tuple[str, str]:
    if r == 0:
        return "Not rated", "White"
    if r < 2.5:
        return "Poor", "Red"
    if r < 3.5:
        return "Average", "Orange"
    if r < 4.0:
        return "Good", "Yellow"
    if r < 4.5:
        return "Very Good", "Green"
    return "Excellent", "Dark Green"


def generate(n: int = 3000, seed: int = 42) -> pd.DataFrame:
    """Return ``n`` (+ a few injected duplicates) raw-format rows as strings."""
    rng = np.random.default_rng(seed)
    countries = io.read_country_seed().set_index("country_code")
    fx = io.read_fx_seed().set_index("iso_currency")["gbp_per_unit"]

    codes = np.array(list(_MARKETS))
    weights = np.array([m[0] for m in _MARKETS.values()])
    country_code = rng.choice(codes, size=n, p=weights / weights.sum())

    rows = []
    for i, cc in enumerate(country_code):
        _, currency_label, cities = _MARKETS[int(cc)]
        city = cities[min(int(rng.geometric(0.45)) - 1, len(cities) - 1)]
        price = int(rng.choice([1, 2, 3, 4], p=[0.45, 0.33, 0.15, 0.07]))
        delivery = bool(cc == 1 and rng.random() < 0.33 - 0.05 * (price - 2))
        booking = bool(rng.random() < [0.02, 0.10, 0.45, 0.65][price - 1])

        gbp_cost = rng.lognormal(np.log(_GBP_COST_BY_PRICE[price]), 0.35)
        rate = fx[countries.loc[cc, "iso_currency"]]
        local_cost = int(round(gbp_cost / rate, -1 if rate < 0.1 else 0))

        unrated = rng.random() < (0.25 if cc == 1 else 0.03)
        if unrated:
            rating, votes = 0.0, int(rng.integers(0, 4))
        else:
            market_shift = 0.4 if cc != 1 else 0.0
            mu = 3.0 + 0.22 * (price - 1) + 0.12 * delivery + 0.15 * booking + market_shift
            rating = float(np.clip(round(rng.normal(mu, 0.45), 1), 1.8, 4.9))
            votes = int(rng.lognormal(2.5 + 1.1 * (rating - 2.5), 0.9))
        text, color = _rating_text_color(rating)

        k = int(rng.choice([1, 2, 3, 4], p=[0.35, 0.35, 0.2, 0.1]))
        pool = _CUISINES + (["British", "Cafe", "Pub Food"] if cc == 215 else [])
        cuisines = ", ".join(rng.choice(pool, size=k, replace=False))

        lat0, lon0 = {1: (28.6, 77.2), 215: (51.5, -0.12), 216: (28.5, -81.4)}.get(
            int(cc), (10.0, 50.0)
        )
        rows.append(
            {
                "Restaurant ID": str(100000 + i),
                "Restaurant Name": f"Restaurant {i:05d}",
                "Country Code": str(cc),
                "City": city,
                "Address": f"{int(rng.integers(1, 300))} High Street, {city}",
                "Locality": f"{city} Central",
                "Locality Verbose": f"{city} Central, {city}",
                "Longitude": f"{lon0 + rng.normal(0, 0.1):.6f}",
                "Latitude": f"{lat0 + rng.normal(0, 0.1):.6f}",
                "Cuisines": cuisines,
                "Average Cost for two": str(local_cost),
                "Currency": currency_label,
                "Has Table booking": "Yes" if booking else "No",
                "Has Online delivery": "Yes" if delivery else "No",
                "Is delivering now": "Yes" if delivery and rng.random() < 0.01 else "No",
                "Switch to order menu": "No",
                "Price range": str(price),
                "Aggregate rating": f"{rating:.1f}",
                "Rating color": color,
                "Rating text": text,
                "Votes": str(votes),
            }
        )
    df = pd.DataFrame(rows, columns=RAW_COLUMNS)

    # Inject the source file's known defects.
    idx = rng.choice(n, size=max(5, n // 100), replace=False)
    df.loc[idx[0:2], "Average Cost for two"] = "0"
    df.loc[idx[2:4], ["Latitude", "Longitude"]] = "0"
    df.loc[idx[4:5], "Cuisines"] = ""
    jakarta = df.index[df["City"] == "Jakarta"]
    if len(jakarta):
        df.loc[jakarta[0], "Average Cost for two"] = "800000"
    india = df.index[df["Country Code"] == "1"]
    df.loc[india[:2], "Average Cost for two"] = "250000"  # implausible INR values
    df = pd.concat([df, df.sample(3, random_state=seed)], ignore_index=True)
    return df


def write_sample(path: str | Path, n: int = 3000, seed: int = 42) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    generate(n, seed).to_csv(path, index=False, encoding="utf-8")
    return path
