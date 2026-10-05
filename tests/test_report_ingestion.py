from decimal import Decimal
from pathlib import Path

from data.report_ingestion import ingest_all_reports


RAW_DATA_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
)


def test_ingests_all_four_reports():
    observations = ingest_all_reports(RAW_DATA_DIR)

    assert len(observations) == 4


def test_ingests_t02_field_report():
    observations = ingest_all_reports(RAW_DATA_DIR)

    t02 = next(
        observation
        for observation in observations
        if observation.trial_id == "T02"
    )

    assert t02.crop == "Wheat"
    assert t02.product == "Harvest Plus"
    assert t02.country == "Germany"
    assert t02.year == 2024
    assert t02.trial_type == "Demonstration"

    assert t02.treatment_yield_kg_ha == Decimal("7800")
    assert t02.control_yield_kg_ha == Decimal("7500")

    assert t02.source_name == "T02_field_report.txt"
    assert t02.source_type == "report"


def test_ingests_t03_summary():
    observations = ingest_all_reports(RAW_DATA_DIR)

    t03 = next(
        observation
        for observation in observations
        if observation.trial_id == "T03"
    )

    assert t03.crop == "Potato"
    assert t03.product == "Root Boost"
    assert t03.country == "Spain"
    assert t03.year == 2023
    assert t03.trial_type == "Demonstration"

    assert t03.treatment_yield_kg_ha == Decimal("44000")
    assert t03.control_yield_kg_ha == Decimal("40000")


def test_ingests_t04_scientific_report():
    observations = ingest_all_reports(RAW_DATA_DIR)

    t04 = next(
        observation
        for observation in observations
        if observation.trial_id == "T04"
    )

    assert t04.crop == "Potato"
    assert t04.product == "Root Boost"
    assert t04.country == "France"
    assert t04.year == 2024
    assert t04.trial_type == "Scientific"

    assert t04.treatment_yield_kg_ha == Decimal("45000")
    assert t04.control_yield_kg_ha == Decimal("45000")


def test_ingests_t06_archive_note():
    observations = ingest_all_reports(RAW_DATA_DIR)

    t06 = next(
        observation
        for observation in observations
        if observation.trial_id == "T06"
    )

    assert t06.crop == "Wheat"
    assert t06.product == "Harvest Plus"
    assert t06.country == "Spain"
    assert t06.year == 2021
    assert t06.trial_type == "Scientific"

    assert t06.treatment_yield_kg_ha == Decimal("6600")
    assert t06.control_yield_kg_ha == Decimal("6000")