from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from models.quality import (
    DataQualityIssue,
    IssueType,
    Severity,
)
from models.trial import TrialObservation


def group_observations_by_trial(
    observations: Iterable[TrialObservation],
) -> dict[str, list[TrialObservation]]:
    """
    Group source observations by their logical trial ID.
    """

    grouped: dict[str, list[TrialObservation]] = defaultdict(list)

    for observation in observations:
        grouped[observation.trial_id].append(observation)

    return dict(grouped)


def _source_names(
    observations: list[TrialObservation],
) -> list[str]:
    return sorted(
        {
            observation.source_name
            for observation in observations
        }
    )


def _metadata_fields() -> tuple[str, ...]:
    return (
        "crop",
        "product",
        "country",
        "year",
        "trial_type",
    )


def _get_field_value(
    observation: TrialObservation,
    field_name: str,
):
    return getattr(observation, field_name)


def detect_metadata_conflicts(
    trial_id: str,
    observations: list[TrialObservation],
) -> list[DataQualityIssue]:
    """
    Detect disagreements in trial metadata across sources.
    """

    issues: list[DataQualityIssue] = []

    for field_name in _metadata_fields():
        values = {
            _get_field_value(observation, field_name)
            for observation in observations
        }

        if len(values) <= 1:
            continue

        formatted_values = ", ".join(
            sorted(str(value) for value in values)
        )

        issues.append(
            DataQualityIssue(
                trial_id=trial_id,
                issue_type=IssueType.CONFLICT,
                severity=Severity.ERROR,
                field_name=field_name,
                description=(
                    f"Conflicting {field_name} values across "
                    f"sources: {formatted_values}."
                ),
                source_names=_source_names(observations),
            )
        )

    return issues


def detect_yield_conflicts(
    trial_id: str,
    observations: list[TrialObservation],
) -> list[DataQualityIssue]:
    """
    Detect disagreements in treatment/control yield values.

    Missing values are ignored here because they are handled separately.
    """

    issues: list[DataQualityIssue] = []

    yield_fields = (
        (
            "treatment_yield_kg_ha",
            "treatment yield",
        ),
        (
            "control_yield_kg_ha",
            "control yield",
        ),
    )

    for field_name, display_name in yield_fields:
        values = {
            getattr(observation, field_name)
            for observation in observations
            if getattr(observation, field_name) is not None
        }

        if len(values) <= 1:
            continue

        formatted_values = ", ".join(
            f"{value:.0f} kg/ha"
            for value in sorted(values)
        )

        issues.append(
            DataQualityIssue(
                trial_id=trial_id,
                issue_type=IssueType.CONFLICT,
                severity=Severity.ERROR,
                field_name=field_name,
                description=(
                    f"Conflicting {display_name} values across "
                    f"sources: {formatted_values}."
                ),
                source_names=_source_names(observations),
            )
        )

    return issues


def detect_missing_values(
    trial_id: str,
    observations: list[TrialObservation],
) -> list[DataQualityIssue]:
    """
    Detect missing treatment/control yields.

    A missing value in one source is only reported when that
    source actually lacks the value. We do not infer a value
    from another source.
    """

    issues: list[DataQualityIssue] = []

    yield_fields = (
        (
            "treatment_yield_kg_ha",
            "treatment yield",
        ),
        (
            "control_yield_kg_ha",
            "control yield",
        ),
    )

    for observation in observations:
        for field_name, display_name in yield_fields:
            value = getattr(observation, field_name)

            if value is not None:
                continue

            issues.append(
                DataQualityIssue(
                    trial_id=trial_id,
                    issue_type=IssueType.MISSING_VALUE,
                    severity=Severity.WARNING,
                    field_name=field_name,
                    description=(
                        f"{display_name.capitalize()} is missing "
                        f"in source {observation.source_name}."
                    ),
                    source_names=[observation.source_name],
                )
            )

    return issues


def detect_duplicate_observations(
    trial_id: str,
    observations: list[TrialObservation],
) -> list[DataQualityIssue]:
    """
    Detect multiple sources that contain equivalent observations.

    A duplicate means the normalized trial metadata and available
    yield values are equivalent across sources.
    """

    if len(observations) < 2:
        return []

    issues: list[DataQualityIssue] = []

    reference = observations[0]

    for other in observations[1:]:
        equivalent = (
            reference.crop == other.crop
            and reference.product == other.product
            and reference.country == other.country
            and reference.year == other.year
            and reference.trial_type == other.trial_type
            and reference.treatment_yield_kg_ha
            == other.treatment_yield_kg_ha
            and reference.control_yield_kg_ha
            == other.control_yield_kg_ha
        )

        if not equivalent:
            continue

        issues.append(
            DataQualityIssue(
                trial_id=trial_id,
                issue_type=IssueType.DUPLICATE,
                severity=Severity.INFO,
                description=(
                    "Equivalent trial observation found in "
                    f"{reference.source_name} and "
                    f"{other.source_name}."
                ),
                source_names=sorted(
                    [
                        reference.source_name,
                        other.source_name,
                    ]
                ),
            )
        )

    return issues


def detect_single_source(
    trial_id: str,
    observations: list[TrialObservation],
) -> list[DataQualityIssue]:
    """
    Flag trials supported by only one source.
    """

    if len(observations) != 1:
        return []

    observation = observations[0]

    return [
        DataQualityIssue(
            trial_id=trial_id,
            issue_type=IssueType.SINGLE_SOURCE,
            severity=Severity.WARNING,
            description=(
                "Trial is supported by only one source: "
                f"{observation.source_name}."
            ),
            source_names=[observation.source_name],
        )
    ]


def reconcile_trial(
    trial_id: str,
    observations: list[TrialObservation],
) -> list[DataQualityIssue]:
    """
    Run all deterministic quality checks for one logical trial.
    """

    if not observations:
        return []

    issues: list[DataQualityIssue] = []

    issues.extend(
        detect_duplicate_observations(
            trial_id,
            observations,
        )
    )

    issues.extend(
        detect_metadata_conflicts(
            trial_id,
            observations,
        )
    )

    issues.extend(
        detect_yield_conflicts(
            trial_id,
            observations,
        )
    )

    issues.extend(
        detect_missing_values(
            trial_id,
            observations,
        )
    )

    issues.extend(
        detect_single_source(
            trial_id,
            observations,
        )
    )

    return issues


def reconcile_all(
    observations: Iterable[TrialObservation],
) -> list[DataQualityIssue]:
    """
    Reconcile every logical trial in the supplied observations.
    """

    grouped = group_observations_by_trial(observations)

    issues: list[DataQualityIssue] = []

    for trial_id in sorted(grouped):
        issues.extend(
            reconcile_trial(
                trial_id,
                grouped[trial_id],
            )
        )

    return issues