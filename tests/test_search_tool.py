from pathlib import Path

from data.ingestion import ingest_all_csvs
from data.report_ingestion import ingest_all_reports
from database.repository import (
    load_observations,
    load_raw_file_contents,
)
from database.schema import create_database
from reconciliation.quality import reconcile_all
from tools.search import search_trials


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


def test_search_without_filters_returns_all_trials(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = search_trials(
            connection
        )

        assert len(results) == 6

        assert [
            result["trial_id"]
            for result in results
        ] == [
            "T01",
            "T02",
            "T03",
            "T04",
            "T05",
            "T06",
        ]

    finally:
        connection.close()


def test_search_by_crop(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = search_trials(
            connection,
            crop="Potato",
        )

        assert [
            result["trial_id"]
            for result in results
        ] == [
            "T03",
            "T04",
        ]

    finally:
        connection.close()


def test_search_by_product(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = search_trials(
            connection,
            product="Harvest Plus",
        )

        assert [
            result["trial_id"]
            for result in results
        ] == [
            "T01",
            "T02",
            "T05",
            "T06",
        ]

    finally:
        connection.close()


def test_search_by_multiple_filters(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = search_trials(
            connection,
            crop="Wheat",
            product="Harvest Plus",
            country="Germany",
        )

        assert [
            result["trial_id"]
            for result in results
        ] == [
            "T02",
            "T05",
        ]

    finally:
        connection.close()


def test_search_returns_evidence_status(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = search_trials(
            connection,
            trial_type="Demonstration",
        )

        statuses = {
            result["trial_id"]: result["evidence_status"]
            for result in results
        }

        assert statuses == {
            "T02": "consistent",
            "T03": "conflict",
            "T05": "incomplete",
        }

    finally:
        connection.close()


def test_search_with_no_matches_returns_empty_list(
    tmp_path,
):
    connection = _build_database(
        tmp_path
    )

    try:
        results = search_trials(
            connection,
            country="Italy",
        )

        assert results == []

    finally:
        connection.close()