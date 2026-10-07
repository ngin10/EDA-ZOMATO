"""Static charts for the report (PNG). One visual system for every chart:
recessive axes, one accent hue for the subject of the chart, neutral grey for
context, direct labels instead of a legend wherever the series count allows.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"  # primary series / sequential hue
ORANGE = "#eb6834"  # second series / highlight (UK)
NEUTRAL = "#b9b8b3"  # context bars

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": TEXT_2,
        "axes.titlecolor": TEXT,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "font.size": 10,
        "legend.frameon": False,
    }
)


def _finish(fig: plt.Figure, ax: plt.Axes, title: str, subtitle: str, path: Path) -> Path:
    ax.set_title(title, pad=22)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=TEXT_2, fontsize=9, va="bottom")
    ax.set_axisbelow(True)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _hbar(ax: plt.Axes, labels, values, colors, fmt: str) -> None:
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors, height=0.62)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    vmax = max(values) if len(values) else 1
    for yi, v in zip(y, values, strict=True):
        ax.text(v + vmax * 0.01, yi, fmt.format(v), va="center", color=TEXT_2, fontsize=9)
    ax.set_xlim(0, vmax * 1.15)


def market_footprint(market: pd.DataFrame, path: Path) -> Path:
    d = market.sort_values("restaurants", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = [ORANGE if c == "United Kingdom" else BLUE for c in d["country"]]
    _hbar(ax, d["country"], d["restaurants"].to_numpy(), colors, "{:,.0f}")
    ax.set_xlabel("Restaurants listed")
    return _finish(
        fig,
        ax,
        "Platform footprint by country",
        "Restaurants listed; United Kingdom highlighted",
        path,
    )


def cost_by_country(market: pd.DataFrame, path: Path) -> Path:
    d = market.dropna(subset=["median_cost_for_two_gbp"]).sort_values(
        "median_cost_for_two_gbp", ascending=False
    )
    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = [ORANGE if c == "United Kingdom" else NEUTRAL for c in d["country"]]
    _hbar(ax, d["country"], d["median_cost_for_two_gbp"].to_numpy(), colors, "£{:,.2f}")
    ax.set_xlabel("Median cost for two (GBP)")
    return _finish(
        fig,
        ax,
        "What does dinner for two cost?",
        "Median cost for two converted to GBP at data-vintage FX; outliers excluded",
        path,
    )


def rating_distribution(df: pd.DataFrame, path: Path) -> Path:
    rated = df.loc[df["is_rated"], "aggregate_rating"].astype(float)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(rated, bins=np.arange(1.75, 5.01, 0.1), color=BLUE, edgecolor=SURFACE, linewidth=1)
    ax.axvline(rated.median(), color=TEXT_2, linestyle="--", linewidth=1)
    ax.text(
        rated.median() + 0.03,
        ax.get_ylim()[1] * 0.92,
        f"median {rated.median():.1f}",
        color=TEXT_2,
        fontsize=9,
    )
    ax.set_xlabel("Aggregate rating")
    ax.set_ylabel("Restaurants")
    ax.grid(axis="x", visible=False)
    n_unrated = int((~df["is_rated"]).sum())
    return _finish(
        fig,
        ax,
        "How are restaurants rated?",
        f"Rated restaurants only; {n_unrated:,} unrated (0.0) listings excluded",
        path,
    )


def rating_by_price_band(df: pd.DataFrame, labels: dict[int, str], path: Path) -> Path:
    rated = df[df["is_rated"]]
    bands = sorted(rated["price_range"].dropna().unique())
    data = [rated.loc[rated["price_range"] == b, "aggregate_rating"].astype(float) for b in bands]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bp = ax.boxplot(
        data,
        patch_artist=True,
        widths=0.5,
        showfliers=False,
        medianprops={"color": TEXT, "linewidth": 1.5},
    )
    for box in bp["boxes"]:
        box.set(facecolor=BLUE, alpha=0.85, edgecolor=BLUE)
    ax.set_xticks(range(1, len(bands) + 1), [f"{labels.get(int(b), b)}\n({int(b)})" for b in bands])
    ax.set_ylabel("Aggregate rating")
    ax.grid(axis="x", visible=False)
    return _finish(
        fig, ax, "Rating by price band", "Rating spread by price band (box = middle 50%)", path
    )


def service_uplift(service: pd.DataFrame, service_name: str, path: Path) -> Path:
    order = ["All", "Budget", "Mid-range", "Premium", "Luxury"]
    d = (
        service[service["service"] == service_name]
        .set_index("price_band")
        .reindex(order)
        .dropna(subset=["rating_with", "rating_without"], how="all")
    )
    x = np.arange(len(d))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x - w / 2 - 0.01, d["rating_without"], w, color=NEUTRAL, label="Without")
    ax.bar(x + w / 2 + 0.01, d["rating_with"], w, color=BLUE, label="With")
    for xi, (a, b) in enumerate(zip(d["rating_without"], d["rating_with"], strict=True)):
        for xpos, v in ((xi - w / 2, a), (xi + w / 2, b)):
            if pd.notna(v):
                ax.text(xpos, v + 0.03, f"{v:.2f}", ha="center", color=TEXT_2, fontsize=8)
    ax.set_xticks(x, d.index)
    lo = np.nanmin(d[["rating_with", "rating_without"]].to_numpy())
    ax.set_ylim(max(0, lo - 0.6), 5)
    ax.set_ylabel("Mean rating (rated restaurants)")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", ncols=2)
    nice = service_name.replace("_", " ")
    return _finish(
        fig,
        ax,
        f"Rating with vs without {nice}",
        "Overall and within price band (controls for the price mix). "
        "Note: y-axis does not start at 0",
        path,
    )


def top_cuisines(cuisine: pd.DataFrame, path: Path, n: int = 12) -> Path:
    d = cuisine.nlargest(n, "restaurants")
    fig, ax = plt.subplots(figsize=(8, 5.5))
    _hbar(ax, d["cuisine"], d["restaurants"].to_numpy(), BLUE, "{:,.0f}")
    ax.set_xlabel("Restaurants offering the cuisine")
    return _finish(
        fig,
        ax,
        "Most widely offered cuisines",
        "Multi-cuisine restaurants count once per cuisine",
        path,
    )


def votes_vs_rating(df: pd.DataFrame, path: Path) -> Path:
    rated = df[df["is_rated"]]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    hb = ax.hexbin(
        rated["votes"].astype(float) + 1,
        rated["aggregate_rating"].astype(float),
        xscale="log",
        gridsize=35,
        cmap="Blues",
        mincnt=1,
        linewidths=0.2,
    )
    cb = fig.colorbar(hb, ax=ax, pad=0.01)
    cb.set_label("Restaurants", color=TEXT_2)
    cb.outline.set_visible(False)
    ax.set_xlabel("Votes + 1 (log scale)")
    ax.set_ylabel("Aggregate rating")
    ax.grid(False)
    return _finish(
        fig,
        ax,
        "Engagement (votes) vs rating",
        "Each hexagon counts restaurants; darker = more",
        path,
    )


def uk_cities(uk_city: pd.DataFrame, path: Path) -> Path | None:
    if uk_city.empty:
        return None
    d = uk_city.sort_values("restaurants", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    _hbar(ax, d["city"], d["restaurants"].to_numpy(), ORANGE, "{:,.0f}")
    ax.set_xlabel("Restaurants listed")
    return _finish(fig, ax, "UK coverage by city", "Restaurants listed in each UK city", path)


def render_all(
    df: pd.DataFrame, tables: dict[str, pd.DataFrame], labels: dict[int, str], out_dir: Path
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        market_footprint(tables["market_overview"], out_dir / "01_market_footprint.png"),
        cost_by_country(tables["market_overview"], out_dir / "02_cost_by_country_gbp.png"),
        rating_distribution(df, out_dir / "03_rating_distribution.png"),
        rating_by_price_band(df, labels, out_dir / "04_rating_by_price_band.png"),
        service_uplift(
            tables["service_impact"], "table_booking", out_dir / "05_table_booking_uplift.png"
        ),
        service_uplift(
            tables["service_impact"], "online_delivery", out_dir / "06_online_delivery_uplift.png"
        ),
        top_cuisines(tables["cuisine_performance"], out_dir / "07_top_cuisines.png"),
        votes_vs_rating(df, out_dir / "08_votes_vs_rating.png"),
        uk_cities(tables["uk_city_summary"], out_dir / "09_uk_cities.png"),
    ]
    return [p for p in paths if p is not None]
