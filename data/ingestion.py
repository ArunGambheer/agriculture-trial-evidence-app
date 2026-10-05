from pathlib import Path

import pandas as pd

from data.normalization import (
    normalize_country,
    normalize_crop,
    normalize_product,
    normalize_trial_type,
    normalize_yield_to_kg_per_ha,
    parse_optional_decimal,
)
from models.trial import TrialObservation


class CSVIngestionError(Exception):
    """Raised when a CSV cannot be converted into canonical observations."""


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise CSVIngestionError(
            f"Unable to read CSV file {path}: {exc}"
        ) from exc


def _require_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    source_name: str,
) -> None:
    actual_columns = set(dataframe.columns)
    missing_columns = required_columns - actual_columns

    if missing_columns:
        raise CSVIngestionError(
            f"{source_name} is missing required columns: "
            f"{sorted(missing_columns)}"
        )


def _ingest_trials_a(
    dataframe: pd.DataFrame,
    source_name: str,
) -> list[TrialObservation]:

    required_columns = {
        "trial_id",
        "crop",
        "product",
        "country",
        "year",
        "trial_type",
        "treatment_yield",
        "control_yield",
        "yield_unit",
    }

    _require_columns(dataframe, required_columns, source_name)

    observations: list[TrialObservation] = []

    for row_number, row in dataframe.iterrows():
        try:
            observation = TrialObservation(
                trial_id=str(row["trial_id"]).strip(),
                crop=normalize_crop(row["crop"]),
                product=normalize_product(row["product"]),
                country=normalize_country(row["country"]),
                year=int(row["year"]),
                trial_type=normalize_trial_type(row["trial_type"]),
                treatment_yield_kg_ha=normalize_yield_to_kg_per_ha(
                    row["treatment_yield"],
                    row["yield_unit"],
                ),
                control_yield_kg_ha=normalize_yield_to_kg_per_ha(
                    row["control_yield"],
                    row["yield_unit"],
                ),
                source_name=source_name,
                source_type="csv",
            )

            observations.append(observation)

        except Exception as exc:
            raise CSVIngestionError(
                f"Failed to ingest {source_name}, "
                f"row {row_number + 2}: {exc}"
            ) from exc

    return observations


def _ingest_trials_b(
    dataframe: pd.DataFrame,
    source_name: str,
) -> list[TrialObservation]:

    required_columns = {
        "Trial reference",
        "Crop name",
        "Product name",
        "Country code",
        "Season year",
        "Trial category",
        "Treated yield kg per ha",
        "Untreated yield kg per ha",
    }

    _require_columns(dataframe, required_columns, source_name)

    observations: list[TrialObservation] = []

    for row_number, row in dataframe.iterrows():
        try:
            observation = TrialObservation(
                trial_id=str(row["Trial reference"]).strip(),
                crop=normalize_crop(row["Crop name"]),
                product=normalize_product(row["Product name"]),
                country=normalize_country(row["Country code"]),
                year=int(row["Season year"]),
                trial_type=normalize_trial_type(row["Trial category"]),
                treatment_yield_kg_ha=parse_optional_decimal(
                    row["Treated yield kg per ha"]
                ),
                control_yield_kg_ha=parse_optional_decimal(
                    row["Untreated yield kg per ha"]
                ),
                source_name=source_name,
                source_type="csv",
            )

            observations.append(observation)

        except Exception as exc:
            raise CSVIngestionError(
                f"Failed to ingest {source_name}, "
                f"row {row_number + 2}: {exc}"
            ) from exc

    return observations


def ingest_csv(path: str | Path) -> list[TrialObservation]:
    """
    Ingest one supported CSV source and convert it into
    canonical TrialObservation objects.
    """

    csv_path = Path(path)
    dataframe = _read_csv(csv_path)
    source_name = csv_path.name

    columns = set(dataframe.columns)

    trials_a_columns = {
        "trial_id",
        "crop",
        "product",
        "country",
        "year",
        "trial_type",
        "treatment_yield",
        "control_yield",
        "yield_unit",
    }

    trials_b_columns = {
        "Trial reference",
        "Crop name",
        "Product name",
        "Country code",
        "Season year",
        "Trial category",
        "Treated yield kg per ha",
        "Untreated yield kg per ha",
    }

    if trials_a_columns.issubset(columns):
        return _ingest_trials_a(dataframe, source_name)

    if trials_b_columns.issubset(columns):
        return _ingest_trials_b(dataframe, source_name)

    raise CSVIngestionError(
        f"Unsupported CSV schema in {source_name}. "
        f"Columns found: {sorted(columns)}"
    )


def ingest_all_csvs(
    directory: str | Path,
) -> list[TrialObservation]:
    """
    Ingest every CSV file in a directory.

    Each supported source schema is converted into the same
    canonical TrialObservation representation.
    """

    raw_directory = Path(directory)

    if not raw_directory.exists():
        raise FileNotFoundError(
            f"Raw data directory not found: {raw_directory}"
        )

    csv_files = sorted(raw_directory.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {raw_directory}"
        )

    observations: list[TrialObservation] = []

    for csv_file in csv_files:
        observations.extend(ingest_csv(csv_file))

    return observations