from pathlib import Path
import re

from data.normalization import (
    normalize_country,
    normalize_crop,
    normalize_product,
    normalize_trial_type,
    normalize_yield_to_kg_per_ha,
)
from models.trial import TrialObservation


class ReportIngestionError(Exception):
    """Raised when a text report cannot be converted into an observation."""


def _read_report(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Report file not found: {path}")

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ReportIngestionError(
            f"Unable to decode report {path} as UTF-8."
        ) from exc
    except OSError as exc:
        raise ReportIngestionError(
            f"Unable to read report {path}: {exc}"
        ) from exc


def _extract_required(
    pattern: str,
    text: str,
    field_name: str,
    source_name: str,
) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if not match:
        raise ReportIngestionError(
            f"Could not extract {field_name} from {source_name}."
        )

    value = match.group(1).strip()

    if not value:
        raise ReportIngestionError(
            f"Extracted empty {field_name} from {source_name}."
        )

    return value


def _extract_trial_id(text: str, source_name: str) -> str:
    return _extract_required(
        r"\bTrial\s+(T\d+)\b",
        text,
        "trial_id",
        source_name,
    )


def _extract_crop(text: str, source_name: str) -> str:
    return _extract_required(
        r"\bCrop:\s*([^\.\r\n]+)",
        text,
        "crop",
        source_name,
    )


def _extract_product(text: str, source_name: str) -> str:
    return _extract_required(
        r"\bProduct:\s*([^\.\r\n]+)",
        text,
        "product",
        source_name,
    )


def _extract_country(text: str, source_name: str) -> str:
    """
    Reports use either:
        Country: Spain
    or:
        Location: Germany
    """
    return _extract_required(
        r"\b(?:Country|Location):\s*([^\.\r\n]+)",
        text,
        "country",
        source_name,
    )


def _extract_year(text: str, source_name: str) -> int:
    value = _extract_required(
        r"\bYear:\s*(\d{4})\b",
        text,
        "year",
        source_name,
    )

    try:
        return int(value)
    except ValueError as exc:
        raise ReportIngestionError(
            f"Invalid year {value!r} in {source_name}."
        ) from exc


def _extract_trial_type(text: str, source_name: str) -> str:
    return _extract_required(
        r"\bTrial type:\s*([^\.\r\n]+)",
        text,
        "trial_type",
        source_name,
    )


def _extract_treatment_yield(
    text: str,
    source_name: str,
):
    """
    Reports use either:
        Treated yield: 7.8 t/ha
    or:
        Treatment yield: 45 t/ha
    """
    value = _extract_required(
        r"\b(?:Treated|Treatment)\s+yield:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*(t/ha|kg/ha)\b",
        text,
        "treatment_yield",
        source_name,
    )

    match = re.search(
        r"\b(?:Treated|Treatment)\s+yield:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*(t/ha|kg/ha)\b",
        text,
        flags=re.IGNORECASE,
    )

    assert match is not None

    numeric_value = match.group(1)
    unit = match.group(2)

    return normalize_yield_to_kg_per_ha(
        numeric_value,
        unit,
    )


def _extract_control_yield(
    text: str,
    source_name: str,
):
    """
    Reports use either:
        Untreated yield: 7.5 t/ha
    or:
        Control yield: 40 t/ha
    """
    match = re.search(
        r"\b(?:Untreated|Control)\s+"
        r"(?:yield):\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*(t/ha|kg/ha)\b",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        raise ReportIngestionError(
            f"Could not extract control_yield from {source_name}."
        )

    numeric_value = match.group(1)
    unit = match.group(2)

    return normalize_yield_to_kg_per_ha(
        numeric_value,
        unit,
    )


def ingest_report(path: str | Path) -> TrialObservation:
    """
    Ingest one supported text report and convert it into
    the canonical TrialObservation representation.
    """

    report_path = Path(path)
    source_name = report_path.name

    text = _read_report(report_path)

    try:
        return TrialObservation(
            trial_id=_extract_trial_id(text, source_name),
            crop=normalize_crop(
                _extract_crop(text, source_name)
            ),
            product=normalize_product(
                _extract_product(text, source_name)
            ),
            country=normalize_country(
                _extract_country(text, source_name)
            ),
            year=_extract_year(text, source_name),
            trial_type=normalize_trial_type(
                _extract_trial_type(text, source_name)
            ),
            treatment_yield_kg_ha=_extract_treatment_yield(
                text,
                source_name,
            ),
            control_yield_kg_ha=_extract_control_yield(
                text,
                source_name,
            ),
            source_name=source_name,
            source_type="report",
        )

    except ReportIngestionError:
        raise

    except Exception as exc:
        raise ReportIngestionError(
            f"Failed to ingest {source_name}: {exc}"
        ) from exc


def ingest_all_reports(
    directory: str | Path,
) -> list[TrialObservation]:
    """
    Ingest every supported text report in a directory.
    """

    report_directory = Path(directory)

    if not report_directory.exists():
        raise FileNotFoundError(
            f"Report directory not found: {report_directory}"
        )

    report_files = sorted(
        report_directory.glob("*.txt")
    )

    if not report_files:
        raise FileNotFoundError(
            f"No text reports found in {report_directory}"
        )

    observations: list[TrialObservation] = []

    for report_file in report_files:
        observations.append(
            ingest_report(report_file)
        )

    return observations