from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from models.quality import DataQualityIssue, IssueType
from models.trial import TrialObservation


def _decimal_to_string(
    value: Decimal | None,
) -> str | None:
    """
    Convert Decimal to a stable non-scientific string for SQLite.
    """
    if value is None:
        return None

    return f"{value:f}"


def _observation_values(
    observation: TrialObservation,
) -> list[tuple[str, str | None, str | None, str | None]]:
    """
    Convert canonical observation fields into source-result records.

    Returns:
        (field_name, raw_value, normalized_value, unit)
    """

    return [
        (
            "treatment_yield_kg_ha",
            _decimal_to_string(
                observation.treatment_yield_kg_ha
            ),
            _decimal_to_string(
                observation.treatment_yield_kg_ha
            ),
            "kg/ha",
        ),
        (
            "control_yield_kg_ha",
            _decimal_to_string(
                observation.control_yield_kg_ha
            ),
            _decimal_to_string(
                observation.control_yield_kg_ha
            ),
            "kg/ha",
        ),
    ]


def _calculate_evidence_status(
    observations: list[TrialObservation],
    issues: list[DataQualityIssue],
) -> str:
    """
    Calculate a high-level evidence status.

    This is only a summary status. Detailed evidence remains in
    source_results and data_quality_issues.
    """

    issue_types = {
        issue.issue_type
        for issue in issues
    }

    if IssueType.CONFLICT in issue_types:
        return "conflict"

    if IssueType.MISSING_VALUE in issue_types:
        return "incomplete"

    if len(observations) == 1:
        return "single_source"

    return "consistent"


def insert_trial(
    connection: sqlite3.Connection,
    observation: TrialObservation,
    evidence_status: str,
) -> None:
    """
    Insert one logical trial if it does not already exist.
    """

    connection.execute(
        """
        INSERT INTO trials (
            trial_id,
            crop,
            product,
            country,
            year,
            trial_type,
            evidence_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(trial_id) DO UPDATE SET
            evidence_status = excluded.evidence_status
        """,
        (
            observation.trial_id,
            observation.crop,
            observation.product,
            observation.country,
            observation.year,
            observation.trial_type,
            evidence_status,
        ),
    )


def insert_source(
    connection: sqlite3.Connection,
    observation: TrialObservation,
    raw_content: str | None = None,
) -> int:
    """
    Insert a source for a trial and return its source ID.

    If the source already exists for the trial, its existing ID
    is returned.
    """

    cursor = connection.execute(
        """
        INSERT INTO sources (
            trial_id,
            source_name,
            source_type,
            raw_content
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(trial_id, source_name)
        DO UPDATE SET
            source_type = excluded.source_type,
            raw_content = COALESCE(
                excluded.raw_content,
                sources.raw_content
            )
        RETURNING source_id
        """,
        (
            observation.trial_id,
            observation.source_name,
            observation.source_type,
            raw_content,
        ),
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError(
            "Unable to retrieve source ID."
        )

    return int(row[0])


def insert_source_results(
    connection: sqlite3.Connection,
    source_id: int,
    observation: TrialObservation,
) -> None:
    """
    Insert treatment/control yield observations for a source.
    """

    for (
        field_name,
        raw_value,
        normalized_value,
        unit,
    ) in _observation_values(observation):

        connection.execute(
            """
            INSERT INTO source_results (
                source_id,
                field_name,
                raw_value,
                normalized_value,
                unit
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source_id, field_name)
            DO UPDATE SET
                raw_value = excluded.raw_value,
                normalized_value = excluded.normalized_value,
                unit = excluded.unit
            """,
            (
                source_id,
                field_name,
                raw_value,
                normalized_value,
                unit,
            ),
        )


def insert_quality_issues(
    connection: sqlite3.Connection,
    issues: Iterable[DataQualityIssue],
) -> None:
    """
    Insert deterministic data-quality findings.
    """

    for issue in issues:
        connection.execute(
            """
            INSERT INTO data_quality_issues (
                trial_id,
                issue_type,
                severity,
                field_name,
                description,
                source_names
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                issue.trial_id,
                issue.issue_type.value,
                issue.severity.value,
                issue.field_name,
                issue.description,
                json.dumps(issue.source_names),
            ),
        )


def load_observations(
    connection: sqlite3.Connection,
    observations: list[TrialObservation],
    issues: list[DataQualityIssue],
    raw_contents: dict[str, str] | None = None,
) -> None:
    """
    Load canonical observations and quality findings into SQLite.

    This function preserves all source observations. It does not
    choose one source as the truth when sources conflict.
    """

    raw_contents = raw_contents or {}

    grouped: dict[
        str,
        list[TrialObservation],
    ] = {}

    for observation in observations:
        grouped.setdefault(
            observation.trial_id,
            [],
        ).append(observation)

    issues_by_trial: dict[
        str,
        list[DataQualityIssue],
    ] = {}

    for issue in issues:
        issues_by_trial.setdefault(
            issue.trial_id,
            [],
        ).append(issue)

    with connection:
        for trial_id in sorted(grouped):
            trial_observations = grouped[trial_id]

            trial_issues = issues_by_trial.get(
                trial_id,
                [],
            )

            evidence_status = _calculate_evidence_status(
                trial_observations,
                trial_issues,
            )

            first_observation = trial_observations[0]

            insert_trial(
                connection,
                first_observation,
                evidence_status,
            )

            for observation in trial_observations:
                raw_content = raw_contents.get(
                    observation.source_name
                )

                source_id = insert_source(
                    connection,
                    observation,
                    raw_content,
                )

                insert_source_results(
                    connection,
                    source_id,
                    observation,
                )

        insert_quality_issues(
            connection,
            issues,
        )


def load_raw_file_contents(
    raw_directory: str | Path,
) -> dict[str, str]:
    """
    Read raw source files for provenance storage.

    Only CSV and TXT files in the supplied directory are loaded.
    """

    directory = Path(raw_directory)

    if not directory.exists():
        raise FileNotFoundError(
            f"Raw data directory not found: {directory}"
        )

    contents: dict[str, str] = {}

    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in {
            ".csv",
            ".txt",
        }:
            continue

        contents[path.name] = path.read_text(
            encoding="utf-8"
        )

    return contents