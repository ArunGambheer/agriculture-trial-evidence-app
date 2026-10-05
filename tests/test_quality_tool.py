from pathlib import Path

from data.ingestion import ingest_all_csvs
from data.report_ingestion import ingest_all_reports
from database.repository import (
    load_observations,
    load_raw_file_contents,
)
from database.schema import create_database
from reconciliation.quality import reconcile_all
from tools.quality import find_data_quality_issues


RAW_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
)


def _build_database(tmp_path):
    database_path = tmp_path / "trials.db"

    connection = create_database(
        database_path
    )

    observations = (
        ingest_all_csvs(RAW_DIRECTORY)
        + ingest_all_reports(RAW_DIRECTORY)
    )

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


def test_returns_all_quality_issues(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = find_data_quality_issues(
            connection
        )

        assert len(results) > 0

        assert {
            result["trial_id"]
            for result in results
        } == {
            "T01",
            "T02",
            "T03",
            "T04",
            "T05",
            "T06",
        }

    finally:
        connection.close()


def test_filters_issues_by_trial(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = find_data_quality_issues(
            connection,
            trial_id="T03",
        )

        assert len(results) == 1

        assert results[0]["trial_id"] == "T03"
        assert results[0]["issue_type"] == "conflict"
        assert (
            results[0]["field_name"]
            == "treatment_yield_kg_ha"
        )

    finally:
        connection.close()


def test_filters_conflicts(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = find_data_quality_issues(
            connection,
            issue_type="conflict",
        )

        assert len(results) == 1

        assert results[0]["trial_id"] == "T03"

    finally:
        connection.close()


def test_filters_warnings(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = find_data_quality_issues(
            connection,
            severity="warning",
        )

        trial_ids = {
            result["trial_id"]
            for result in results
        }

        assert trial_ids == {
            "T05",
            "T06",
        }

    finally:
        connection.close()


def test_combines_filters(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = find_data_quality_issues(
            connection,
            issue_type="missing_value",
            severity="warning",
        )

        assert len(results) == 1

        assert results[0]["trial_id"] == "T05"
        assert (
            results[0]["field_name"]
            == "control_yield_kg_ha"
        )

    finally:
        connection.close()


def test_no_matching_issues_returns_empty_list(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = find_data_quality_issues(
            connection,
            trial_id="T99",
        )

        assert results == []

    finally:
        connection.close()