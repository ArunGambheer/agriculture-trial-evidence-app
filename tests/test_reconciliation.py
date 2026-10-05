from data.ingestion import ingest_all_csvs
from data.report_ingestion import ingest_all_reports
from models.quality import IssueType, Severity
from reconciliation.quality import (
    group_observations_by_trial,
    reconcile_all,
)


def _load_all_observations():
    from pathlib import Path

    raw_directory = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "raw"
    )

    csv_observations = ingest_all_csvs(raw_directory)
    report_observations = ingest_all_reports(raw_directory)

    return csv_observations + report_observations


def test_groups_observations_into_six_logical_trials():
    observations = _load_all_observations()

    grouped = group_observations_by_trial(observations)

    assert set(grouped.keys()) == {
        "T01",
        "T02",
        "T03",
        "T04",
        "T05",
        "T06",
    }

    assert len(grouped["T01"]) == 2
    assert len(grouped["T02"]) == 2
    assert len(grouped["T03"]) == 2
    assert len(grouped["T04"]) == 2
    assert len(grouped["T05"]) == 1
    assert len(grouped["T06"]) == 1


def test_detects_t01_as_duplicate():
    observations = _load_all_observations()

    issues = reconcile_all(observations)

    t01_issues = [
        issue
        for issue in issues
        if issue.trial_id == "T01"
    ]

    assert len(t01_issues) == 1
    assert t01_issues[0].issue_type == IssueType.DUPLICATE
    assert t01_issues[0].severity == Severity.INFO


def test_detects_t03_treatment_yield_conflict():
    observations = _load_all_observations()

    issues = reconcile_all(observations)

    t03_conflicts = [
        issue
        for issue in issues
        if issue.trial_id == "T03"
        and issue.issue_type == IssueType.CONFLICT
        and issue.field_name == "treatment_yield_kg_ha"
    ]

    assert len(t03_conflicts) == 1

    description = t03_conflicts[0].description

    assert "42000 kg/ha" in description
    assert "44000 kg/ha" in description


def test_detects_t05_missing_control_yield():
    observations = _load_all_observations()

    issues = reconcile_all(observations)

    t05_missing = [
        issue
        for issue in issues
        if issue.trial_id == "T05"
        and issue.issue_type == IssueType.MISSING_VALUE
        and issue.field_name == "control_yield_kg_ha"
    ]

    assert len(t05_missing) == 1
    assert t05_missing[0].severity == Severity.WARNING


def test_detects_t06_single_source():
    observations = _load_all_observations()

    issues = reconcile_all(observations)

    t06_single_source = [
        issue
        for issue in issues
        if issue.trial_id == "T06"
        and issue.issue_type == IssueType.SINGLE_SOURCE
    ]

    assert len(t06_single_source) == 1
    assert t06_single_source[0].severity == Severity.WARNING


def test_consistent_trials_have_no_conflicts():
    observations = _load_all_observations()

    issues = reconcile_all(observations)

    conflicting_trial_ids = {
        issue.trial_id
        for issue in issues
        if issue.issue_type == IssueType.CONFLICT
    }

    assert conflicting_trial_ids == {"T03"}