from __future__ import annotations

import sqlite3
from typing import Optional

from data.normalization import (
    normalize_country,
    normalize_crop,
    normalize_product,
    normalize_trial_type,
)


def search_trials(
    connection: sqlite3.Connection,
    crop: Optional[str] = None,
    product: Optional[str] = None,
    country: Optional[str] = None,
    year: Optional[int] = None,
    trial_type: Optional[str] = None,
) -> list[dict]:
    """
    Search logical trials using optional structured filters.

    Search inputs are normalized before querying the canonical database.
    This prevents harmless differences in capitalization, naming, and
    country representation from causing false "no results" responses.

    Examples:
        wheat -> Wheat
        HARVESTPLUS -> Harvest Plus
        RootBoost -> Root Boost
        potatoes -> Potato
        DE -> Germany
        scientific -> Scientific
    """

    normalized_crop = (
        normalize_crop(crop)
        if crop is not None
        else None
    )

    normalized_product = (
        normalize_product(product)
        if product is not None
        else None
    )

    normalized_country = (
        normalize_country(country)
        if country is not None
        else None
    )

    normalized_trial_type = (
        normalize_trial_type(trial_type)
        if trial_type is not None
        else None
    )

    query = """
        SELECT
            trial_id,
            crop,
            product,
            country,
            year,
            trial_type,
            evidence_status
        FROM trials
        WHERE 1 = 1
    """

    parameters: list[object] = []

    if normalized_crop is not None:
        query += " AND crop = ?"
        parameters.append(normalized_crop)

    if normalized_product is not None:
        query += " AND product = ?"
        parameters.append(normalized_product)

    if normalized_country is not None:
        query += " AND country = ?"
        parameters.append(normalized_country)

    if year is not None:
        query += " AND year = ?"
        parameters.append(year)

    if normalized_trial_type is not None:
        query += " AND trial_type = ?"
        parameters.append(normalized_trial_type)

    query += " ORDER BY trial_id"

    cursor = connection.execute(
        query,
        parameters,
    )

    rows = cursor.fetchall()

    return [
        {
            "trial_id": row[0],
            "crop": row[1],
            "product": row[2],
            "country": row[3],
            "year": row[4],
            "trial_type": row[5],
            "evidence_status": row[6],
        }
        for row in rows
    ]