from __future__ import annotations

import json
import sqlite3


def find_data_quality_issues(
    connection: sqlite3.Connection,
    trial_id: str | None = None,
    issue_type: str | None = None,
    severity: str | None = None,
) -> list[dict]:
    """
    Retrieve deterministic data-quality findings.

    Optional filters:
    - trial_id
    - issue_type
    - severity

    Results are ordered by trial ID and issue ID.
    """

    query = """
        SELECT
            issue_id,
            trial_id,
            issue_type,
            severity,
            field_name,
            description,
            source_names
        FROM data_quality_issues
        WHERE 1 = 1
    """

    parameters: list[object] = []

    if trial_id is not None:
        query += " AND trial_id = ?"
        parameters.append(trial_id)

    if issue_type is not None:
        query += " AND issue_type = ?"
        parameters.append(issue_type)

    if severity is not None:
        query += " AND severity = ?"
        parameters.append(severity)

    query += """
        ORDER BY
            trial_id,
            issue_id
    """

    rows = connection.execute(
        query,
        parameters,
    ).fetchall()

    return [
        {
            "issue_id": row[0],
            "trial_id": row[1],
            "issue_type": row[2],
            "severity": row[3],
            "field_name": row[4],
            "description": row[5],
            "source_names": json.loads(row[6]),
        }
        for row in rows
    ]