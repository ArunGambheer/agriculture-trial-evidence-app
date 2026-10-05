from pathlib import Path

from data.ingestion import ingest_all_csvs
from data.report_ingestion import ingest_all_reports
from database.repository import (
    load_observations,
    load_raw_file_contents,
)
from database.schema import create_database
from reconciliation.quality import reconcile_all
from tools.compare import compare_trials


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


def test_comparable_trial_returns_correct_improvement(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = compare_trials(
            connection,
            ["T01"],
        )

        comparison = result["trials"][0]

        assert comparison[
            "comparison_status"
        ] == "comparable"

        assert comparison[
            "treatment_yield_kg_ha"
        ] == "8400"

        assert comparison[
            "control_yield_kg_ha"
        ] == "8000"

        assert comparison[
            "yield_difference_kg_ha"
        ] == "400"

        assert comparison[
            "yield_improvement_percent"
        ] == "5.00"

    finally:
        connection.close()


def test_t03_conflict_blocks_comparison(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = compare_trials(
            connection,
            ["T03"],
        )

        comparison = result["trials"][0]

        assert comparison[
            "comparison_status"
        ] == "blocked"

        assert (
            comparison[
                "yield_improvement_percent"
            ]
            is None
        )

        assert "conflicting" in comparison[
            "reason"
        ].lower()

    finally:
        connection.close()


def test_t05_missing_control_is_incomplete(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = compare_trials(
            connection,
            ["T05"],
        )

        comparison = result["trials"][0]

        assert comparison[
            "comparison_status"
        ] == "incomplete"

        assert comparison[
            "treatment_yield_kg_ha"
        ] == "8100"

        assert comparison[
            "control_yield_kg_ha"
        ] is None

        assert comparison[
            "yield_improvement_percent"
        ] is None

    finally:
        connection.close()


def test_multiple_trials_are_compared(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = compare_trials(
            connection,
            [
                "T01",
                "T02",
                "T03",
                "T04",
                "T05",
            ],
        )

        assert result["count"] == 5

        statuses = {
            trial["trial_id"]:
                trial["comparison_status"]
            for trial in result["trials"]
        }

        assert statuses == {
            "T01": "comparable",
            "T02": "comparable",
            "T03": "blocked",
            "T04": "comparable",
            "T05": "incomplete",
        }

    finally:
        connection.close()


def test_unknown_trial_is_reported(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = compare_trials(
            connection,
            ["T99"],
        )

        comparison = result["trials"][0]

        assert comparison[
            "found"
        ] is False

        assert comparison[
            "comparison_status"
        ] == "not_found"

    finally:
        connection.close()


def test_empty_trial_list_returns_empty_result(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = compare_trials(
            connection,
            [],
        )

        assert result == {
            "trials": [],
            "count": 0,
        }

    finally:
        connection.close()