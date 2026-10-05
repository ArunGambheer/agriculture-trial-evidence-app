from pathlib import Path

from data.ingestion import ingest_all_csvs
from data.report_ingestion import ingest_all_reports
from database.repository import (
    load_observations,
    load_raw_file_contents,
)
from database.schema import create_database
from reconciliation.quality import reconcile_all
from tools.evidence import get_trial_evidence


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


def test_returns_none_for_unknown_trial(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = get_trial_evidence(
            connection,
            "T99",
        )

        assert result is None

    finally:
        connection.close()


def test_returns_trial_metadata(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = get_trial_evidence(
            connection,
            "T03",
        )

        assert result is not None

        assert result["trial"] == {
            "trial_id": "T03",
            "crop": "Potato",
            "product": "Root Boost",
            "country": "Spain",
            "year": 2023,
            "trial_type": "Demonstration",
            "evidence_status": "conflict",
        }

    finally:
        connection.close()


def test_returns_all_t03_sources(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = get_trial_evidence(
            connection,
            "T03",
        )

        assert result is not None

        assert [
            source["source_name"]
            for source in result["sources"]
        ] == [
            "T03_summary.txt",
            "trials_a.csv",
        ]

    finally:
        connection.close()


def test_returns_both_conflicting_treatment_values(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = get_trial_evidence(
            connection,
            "T03",
        )

        assert result is not None

        treatment_values = []

        for source in result["sources"]:
            for observation in source["results"]:
                if (
                    observation["field_name"]
                    == "treatment_yield_kg_ha"
                ):
                    treatment_values.append(
                        (
                            source["source_name"],
                            observation[
                                "normalized_value"
                            ],
                        )
                    )

        assert sorted(treatment_values) == [
            ("T03_summary.txt", "44000"),
            ("trials_a.csv", "42000.0"),
        ]

    finally:
        connection.close()


def test_returns_t03_conflict_issue(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = get_trial_evidence(
            connection,
            "T03",
        )

        assert result is not None

        conflicts = [
            issue
            for issue in result["quality_issues"]
            if issue["issue_type"] == "conflict"
        ]

        assert len(conflicts) == 1

        assert (
            conflicts[0]["field_name"]
            == "treatment_yield_kg_ha"
        )

    finally:
        connection.close()


def test_returns_t05_missing_value_issue(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        result = get_trial_evidence(
            connection,
            "T05",
        )

        assert result is not None

        missing = [
            issue
            for issue in result["quality_issues"]
            if issue["issue_type"]
            == "missing_value"
        ]

        assert len(missing) == 1

        assert (
            missing[0]["field_name"]
            == "control_yield_kg_ha"
        )

    finally:
        connection.close()