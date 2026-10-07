import math

import pandas as pd
import pytest

from tests.conftest import make_raw
from zomato_analytics import cleaning, io, quality


def test_fix_mojibake_repairs_reversible_text():
    assert cleaning.fix_mojibake("SÃ£o Paulo") == "São Paulo"
    assert cleaning.fix_mojibake("London") == "London"


def test_irreversible_text_is_flagged_not_dropped():
    df, _ = cleaning.clean(make_raw([{"City": "ÛÁstanbul", "Country Code": "208"}]))
    assert len(df) == 1
    assert bool(df.loc[0, "has_encoding_issue"])


def test_zero_rating_becomes_null_and_unrated():
    df, _ = cleaning.clean(
        make_raw(
            [
                {"Restaurant ID": "1", "Aggregate rating": "0", "Rating text": "Not rated"},
                {"Restaurant ID": "2", "Aggregate rating": "4.5"},
            ]
        )
    )
    assert df["aggregate_rating"].isna().tolist() == [True, False]
    assert df["is_rated"].tolist() == [False, True]


def test_zero_cost_and_null_island_become_null():
    df, _ = cleaning.clean(
        make_raw(
            [
                {"Average Cost for two": "0", "Latitude": "0", "Longitude": "0"},
            ]
        )
    )
    assert math.isnan(df.loc[0, "cost_for_two_local"])
    assert math.isnan(df.loc[0, "latitude"])


def test_duplicates_removed_and_logged():
    df, log = cleaning.clean(
        make_raw([{"Restaurant ID": "1"}, {"Restaurant ID": "1"}, {"Restaurant ID": "2"}])
    )
    assert df["restaurant_id"].tolist() == [1, 2]
    steps = log.to_frame().set_index("step")
    assert steps.loc["drop_duplicates", "rows_affected"] == 1


def test_currency_derived_from_country_not_label():
    # Philippine restaurants are mislabelled "Botswana Pula(P)" in the source file.
    df, _ = cleaning.clean(
        make_raw(
            [
                {
                    "Country Code": "162",
                    "Currency": "Botswana Pula(P)",
                    "Average Cost for two": "1000",
                }
            ]
        )
    )
    fx = io.read_fx_seed().set_index("iso_currency")["gbp_per_unit"]
    assert df.loc[0, "iso_currency"] == "PHP"
    assert df.loc[0, "cost_for_two_gbp"] == pytest.approx(1000 * fx["PHP"], abs=0.01)


def test_gbp_conversion_identity_for_uk():
    df, _ = cleaning.clean(make_raw([{"Average Cost for two": "55"}]))
    assert df.loc[0, "cost_for_two_gbp"] == 55


def test_yes_no_mapped_to_boolean():
    df, _ = cleaning.clean(make_raw([{"Has Table booking": "Yes"}]))
    assert df.loc[0, "has_table_booking"] is True or bool(df.loc[0, "has_table_booking"])


def test_missing_columns_raise_schema_error(tmp_path):
    p = tmp_path / "bad.csv"
    pd.DataFrame({"Restaurant ID": [1]}).to_csv(p, index=False)
    with pytest.raises(io.SchemaError):
        io.read_raw(p)


def test_latin1_file_is_readable(tmp_path):
    p = tmp_path / "latin.csv"
    make_raw([{"City": "Brasília", "Country Code": "30"}]).to_csv(
        p, index=False, encoding="latin-1"
    )
    assert io.read_raw(p).loc[0, "City"] == "Brasília"


def test_cleaned_sample_passes_all_error_checks(df):
    report = quality.assert_clean(df)
    assert (report.loc[report["severity"] == "error", "status"] == "PASS").all()


def test_assert_clean_raises_on_duplicate_key(df):
    broken = pd.concat([df, df.head(1)], ignore_index=True)
    with pytest.raises(quality.DataQualityError):
        quality.assert_clean(broken)


def test_cost_outliers_flagged_within_country(df):
    india = df[df["country"] == "India"]
    flagged = india[india["is_cost_outlier"]]
    assert not flagged.empty
    assert flagged["cost_for_two_local"].min() >= 100_000  # the injected implausible INR values


def test_raw_profile_detects_known_defects(raw):
    profile = quality.profile_raw(raw).set_index("check")
    for check in (
        "duplicate_restaurant_id",
        "zero_rating_means_unrated",
        "currency_label_ambiguous",
        "null_island_coordinates",
    ):
        assert profile.loc[check, "status"] == "FAIL", check
