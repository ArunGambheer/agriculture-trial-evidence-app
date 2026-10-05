from decimal import Decimal
from pathlib import Path

from data.ingestion import ingest_all_csvs


RAW_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def test_ingests_both_csv_formats():
    observations = ingest_all_csvs(RAW_DATA_DIR)

    assert len(observations) == 6


def test_normalizes_trial_a_units_and_names():
    observations = ingest_all_csvs(RAW_DATA_DIR)

    t01_observation = next(
        observation
        for observation in observations
        if observation.trial_id == "T01"
        and observation.source_name == "trials_a.csv"
    )

    assert t01_observation.crop == "Wheat"
    assert t01_observation.product == "Harvest Plus"
    assert t01_observation.country == "France"
    assert t01_observation.trial_type == "Scientific"

    assert t01_observation.treatment_yield_kg_ha == Decimal("8400")
    assert t01_observation.control_yield_kg_ha == Decimal("8000")


def test_normalizes_trial_b_units_and_names():
    observations = ingest_all_csvs(RAW_DATA_DIR)

    t04_observation = next(
        observation
        for observation in observations
        if observation.trial_id == "T04"
    )

    assert t04_observation.crop == "Potato"
    assert t04_observation.product == "Root Boost"
    assert t04_observation.country == "France"
    assert t04_observation.treatment_yield_kg_ha == Decimal("45000")
    assert t04_observation.control_yield_kg_ha == Decimal("45000")


def test_preserves_missing_control_yield():
    observations = ingest_all_csvs(RAW_DATA_DIR)

    t05_observation = next(
        observation
        for observation in observations
        if observation.trial_id == "T05"
    )

    assert t05_observation.treatment_yield_kg_ha == Decimal("8100")
    assert t05_observation.control_yield_kg_ha is None