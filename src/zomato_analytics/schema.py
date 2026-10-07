"""Raw-file contract: expected columns, their clean names and expected types."""

from __future__ import annotations

# Raw column name -> clean snake_case name, in file order.
RAW_TO_CLEAN: dict[str, str] = {
    "Restaurant ID": "restaurant_id",
    "Restaurant Name": "restaurant_name",
    "Country Code": "country_code",
    "City": "city",
    "Address": "address",
    "Locality": "locality",
    "Locality Verbose": "locality_verbose",
    "Longitude": "longitude",
    "Latitude": "latitude",
    "Cuisines": "cuisines",
    "Average Cost for two": "cost_for_two_local",
    "Currency": "currency_label",
    "Has Table booking": "has_table_booking",
    "Has Online delivery": "has_online_delivery",
    "Is delivering now": "is_delivering_now",
    "Switch to order menu": "switch_to_order_menu",
    "Price range": "price_range",
    "Aggregate rating": "aggregate_rating",
    "Rating color": "rating_color",
    "Rating text": "rating_text",
    "Votes": "votes",
}

RAW_COLUMNS: list[str] = list(RAW_TO_CLEAN)

NUMERIC_COLUMNS: list[str] = [
    "restaurant_id",
    "country_code",
    "longitude",
    "latitude",
    "cost_for_two_local",
    "price_range",
    "aggregate_rating",
    "votes",
]

YES_NO_COLUMNS: list[str] = [
    "has_table_booking",
    "has_online_delivery",
    "is_delivering_now",
    "switch_to_order_menu",
]

TEXT_COLUMNS: list[str] = [
    "restaurant_name",
    "city",
    "address",
    "locality",
    "locality_verbose",
    "cuisines",
    "currency_label",
    "rating_color",
    "rating_text",
]

RATING_TEXT_ORDER: list[str] = ["Poor", "Average", "Good", "Very Good", "Excellent"]

# Valid domain ranges used by the data-quality checks.
VALID_RANGES: dict[str, tuple[float, float]] = {
    "aggregate_rating": (0.0, 5.0),
    "price_range": (1, 4),
    "latitude": (-90.0, 90.0),
    "longitude": (-180.0, 180.0),
    "votes": (0, float("inf")),
    "cost_for_two_local": (0, float("inf")),
}
