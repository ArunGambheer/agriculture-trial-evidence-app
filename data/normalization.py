from decimal import Decimal, InvalidOperation
from typing import Optional


PRODUCT_NORMALIZATION = {
    "harvest plus": "Harvest Plus",
    "harvestplus": "Harvest Plus",
    "root boost": "Root Boost",
    "rootboost": "Root Boost",
}


CROP_NORMALIZATION = {
    "wheat": "Wheat",
    "potato": "Potato",
    "potatoes": "Potato",
}


COUNTRY_NORMALIZATION = {
    "fr": "France",
    "france": "France",
    "de": "Germany",
    "germany": "Germany",
    "es": "Spain",
    "spain": "Spain",
}


TRIAL_TYPE_NORMALIZATION = {
    "scientific": "Scientific",
    "demonstration": "Demonstration",
}


def _clean_text(value: object) -> str:
    """Convert a source value into normalized lowercase text."""
    return str(value).strip().lower()


def normalize_product(value: object) -> str:
    key = _clean_text(value)

    if key in PRODUCT_NORMALIZATION:
        return PRODUCT_NORMALIZATION[key]

    return str(value).strip()


def normalize_crop(value: object) -> str:
    key = _clean_text(value)

    if key in CROP_NORMALIZATION:
        return CROP_NORMALIZATION[key]

    return str(value).strip()


def normalize_country(value: object) -> str:
    key = _clean_text(value)

    if key in COUNTRY_NORMALIZATION:
        return COUNTRY_NORMALIZATION[key]

    return str(value).strip()


def normalize_trial_type(value: object) -> str:
    key = _clean_text(value)

    if key in TRIAL_TYPE_NORMALIZATION:
        return TRIAL_TYPE_NORMALIZATION[key]

    return str(value).strip()


def parse_optional_decimal(value: object) -> Optional[Decimal]:
    """
    Convert a source value to Decimal.

    Empty strings and common missing-value representations
    become None.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text or text.lower() in {
        "nan",
        "none",
        "null",
        "missing",
    }:
        return None

    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(
            f"Invalid numeric value: {value!r}"
        ) from exc


def normalize_yield_to_kg_per_ha(
    value: object,
    unit: str,
) -> Optional[Decimal]:
    """
    Convert yield into kg/ha.

    Supported source units:
    - t/ha
    - kg/ha
    """

    numeric_value = parse_optional_decimal(value)

    if numeric_value is None:
        return None

    normalized_unit = _clean_text(unit)

    if normalized_unit == "t/ha":
        return numeric_value * Decimal("1000")

    if normalized_unit == "kg/ha":
        return numeric_value

    raise ValueError(
        f"Unsupported yield unit: {unit!r}. "
        "Expected 't/ha' or 'kg/ha'."
    )