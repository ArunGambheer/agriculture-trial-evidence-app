import sqlite3
from pathlib import Path

from data.ingestion import ingest_all_csvs
from data.report_ingestion import ingest_all_reports
from database.repository import (
    load_observations,
    load_raw_file_contents,
)
from database.schema import create_database
from reconciliation.quality import reconcile_all


RAW_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
)


def _load_all_observations():
    csv_observations = ingest_all_csvs(
        RAW_DIRECTORY
    )

    report_observations = ingest_all_reports(
        RAW_DIRECTORY
    )

    return csv_observations + report_observations


def _build_database(tmp_path):
    database_path = tmp_path / "trials.db"

    connection = create_database(
        database_path
    )

    observations = _load_all_observations()

    issues = reconcile_all(
        observations
    )

    raw_contents = load_raw_file_contents(
        RAW_DIRECTORY
    )

    load_observations(
        connection,
        observations,
        issues,
        raw_contents,
    )

    return connection


def test_create_database_creates_expected_tables(
    tmp_path,
):
    database_path = tmp_path / "trials.db"

    connection = create_database(
        database_path
    )

    try:
        cursor = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        )

        tables = {
            row[0]
            for row in cursor.fetchall()
        }

        assert {
            "data_quality_issues",
            "source_results",
            "sources",
            "trials",
        }.issubset(tables)

    finally:
        connection.close()


def test_database_enables_foreign_keys(
    tmp_path,
):
    database_path = tmp_path / "trials.db"

    connection = create_database(
        database_path
    )

    try:
        result = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()

        assert result == (1,)

    finally:
        connection.close()


def test_loads_six_logical_trials(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        count = connection.execute(
            "SELECT COUNT(*) FROM trials"
        ).fetchone()[0]

        assert count == 6

    finally:
        connection.close()


def test_loads_all_source_observations(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        count = connection.execute(
            "SELECT COUNT(*) FROM sources"
        ).fetchone()[0]

        assert count == 10

    finally:
        connection.close()


def test_t03_preserves_both_conflicting_sources(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        rows = connection.execute(
            """
            SELECT
                s.source_name,
                sr.normalized_value
            FROM source_results sr
            JOIN sources s
                ON s.source_id = sr.source_id
            WHERE s.trial_id = 'T03'
              AND sr.field_name =
                  'treatment_yield_kg_ha'
            ORDER BY
                sr.normalized_value
            """
        ).fetchall()

        assert rows == [
            ("trials_a.csv", "42000.0"),
            ("T03_summary.txt", "44000"),
        ]

    finally:
        connection.close()


def test_t03_is_marked_as_conflict(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        row = connection.execute(
            """
            SELECT evidence_status
            FROM trials
            WHERE trial_id = 'T03'
            """
        ).fetchone()

        assert row == ("conflict",)

    finally:
        connection.close()


def test_t05_is_marked_as_incomplete(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        row = connection.execute(
            """
            SELECT evidence_status
            FROM trials
            WHERE trial_id = 'T05'
            """
        ).fetchone()

        assert row == ("incomplete",)

    finally:
        connection.close()


def test_t06_is_marked_as_single_source(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        row = connection.execute(
            """
            SELECT evidence_status
            FROM trials
            WHERE trial_id = 'T06'
            """
        ).fetchone()

        assert row == ("single_source",)

    finally:
        connection.close()


def test_quality_issues_are_loaded(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM data_quality_issues
            """
        ).fetchone()[0]

        assert count > 0

    finally:
        connection.close()