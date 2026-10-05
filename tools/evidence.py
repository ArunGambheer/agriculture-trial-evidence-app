from __future__ import annotations

import json
import sqlite3


def get_trial_evidence(
    connection: sqlite3.Connection,
    trial_id: str,
) -> dict | None:
    """
    Retrieve a complete evidence view for one logical trial.

    The result includes:
    - canonical trial metadata
    - every supporting source
    - source-level observed results
    - deterministic data-quality issues

    Returns None when the trial does not exist.
    """

    trial_row = connection.execute(
        """
        SELECT
            trial_id,
            crop,
            product,
            country,
            year,
            trial_type,
            evidence_status
        FROM trials
        WHERE trial_id = ?
        """,
        (trial_id,),
    ).fetchone()

    if trial_row is None:
        return None

    trial = {
        "trial_id": trial_row[0],
        "crop": trial_row[1],
        "product": trial_row[2],
        "country": trial_row[3],
        "year": trial_row[4],
        "trial_type": trial_row[5],
        "evidence_status": trial_row[6],
    }

    source_rows = connection.execute(
        """
        SELECT
            source_id,
            source_name,
            source_type,
            raw_content
        FROM sources
        WHERE trial_id = ?
        ORDER BY source_name
        """,
        (trial_id,),
    ).fetchall()

    sources = []

    for source_row in source_rows:
        source_id = source_row[0]

        result_rows = connection.execute(
            """
            SELECT
                field_name,
                raw_value,
                normalized_value,
                unit
            FROM source_results
            WHERE source_id = ?
            ORDER BY field_name
            """,
            (source_id,),
        ).fetchall()

        results = [
            {
                "field_name": row[0],
                "raw_value": row[1],
                "normalized_value": row[2],
                "unit": row[3],
            }
            for row in result_rows
        ]

        sources.append(
            {
                "source_id": source_id,
                "source_name": source_row[1],
                "source_type": source_row[2],
                "raw_content": source_row[3],
                "results": results,
            }
        )

    issue_rows = connection.execute(
        """
        SELECT
            issue_type,
            severity,
            field_name,
            description,
            source_names
        FROM data_quality_issues
        WHERE trial_id = ?
        ORDER BY issue_id
        """,
        (trial_id,),
    ).fetchall()

    issues = [
        {
            "issue_type": row[0],
            "severity": row[1],
            "field_name": row[2],
            "description": row[3],
            "source_names": json.loads(row[4]),
        }
        for row in issue_rows
    ]

    return {
        "trial": trial,
        "sources": sources,
        "quality_issues": issues,
    }