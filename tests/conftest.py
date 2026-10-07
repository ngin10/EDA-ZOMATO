import pandas as pd
import pytest

from zomato_analytics import cleaning, features, sample_data


@pytest.fixture(scope="session")
def raw() -> pd.DataFrame:
    return sample_data.generate(n=1500, seed=7)


@pytest.fixture(scope="session")
def cleaned(raw):
    df, log = cleaning.clean(raw)
    return features.add_features(df), log


@pytest.fixture(scope="session")
def df(cleaned) -> pd.DataFrame:
    return cleaned[0]


def make_raw(rows: list[dict]) -> pd.DataFrame:
    """Build a tiny raw-format frame, filling unspecified columns with valid defaults."""
    base = {
        "Restaurant ID": "1",
        "Restaurant Name": "Test",
        "Country Code": "215",
        "City": "London",
        "Address": "1 High St",
        "Locality": "Soho",
        "Locality Verbose": "Soho, London",
        "Longitude": "-0.13",
        "Latitude": "51.51",
        "Cuisines": "British",
        "Average Cost for two": "40",
        "Currency": "Pounds(£)",
        "Has Table booking": "No",
        "Has Online delivery": "No",
        "Is delivering now": "No",
        "Switch to order menu": "No",
        "Price range": "3",
        "Aggregate rating": "4.2",
        "Rating color": "Green",
        "Rating text": "Very Good",
        "Votes": "120",
    }
    return pd.DataFrame([{**base, **r} for r in rows])
