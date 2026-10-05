from __future__ import annotations

import sqlite3
from decimal import Decimal


def _decimal_to_string(
    value: Decimal,
) -> str:
    """
    Convert Decimal to a clean non-scientific string.

    Whole-number values such as Decimal("8400.0")
    become "8400", while values with meaningful decimal
    precision retain their decimal representation.
    """

    normalized = value.normalize()

    if normalized == normalized.to_integral():
        return str(
            normalized.quantize(
                Decimal("1")
            )
        )

    return format(
        normalized,
        "f",
    )


def _get_trial(
    connection: sqlite3.Connection,
    trial_id: str,
):
    return connection.execute(
        """
        SELECT
            trial_id,
            crop,
            product,
            country,
            year,
            trial_type,
            evidence_status
        FROM trials
        WHERE trial_id = ?
        """,
        (trial_id,),
    ).fetchone()


def _get_yield_values(
    connection: sqlite3.Connection,
    trial_id: str,
):
    rows = connection.execute(
        """
        SELECT
            sr.field_name,
            sr.normalized_value
        FROM source_results sr
        JOIN sources s
            ON s.source_id = sr.source_id
        WHERE s.trial_id = ?
        ORDER BY
            sr.field_name,
            s.source_name
        """,
        (trial_id,),
    ).fetchall()

    treatment_values: list[Decimal] = []
    control_values: list[Decimal] = []

    for field_name, value in rows:
        if value is None:
            continue

        decimal_value = Decimal(value)

        if field_name == "treatment_yield_kg_ha":
            treatment_values.append(decimal_value)

        elif field_name == "control_yield_kg_ha":
            control_values.append(decimal_value)

    return treatment_values, control_values


def _has_issue(
    connection: sqlite3.Connection,
    trial_id: str,
    issue_type: str,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM data_quality_issues
        WHERE trial_id = ?
          AND issue_type = ?
        LIMIT 1
        """,
        (
            trial_id,
            issue_type,
        ),
    ).fetchone()

    return row is not None


def _comparison_for_trial(
    connection: sqlite3.Connection,
    trial_id: str,
) -> dict:
    trial = _get_trial(
        connection,
        trial_id,
    )

    if trial is None:
        return {
            "trial_id": trial_id,
            "found": False,
            "comparison_status": "not_found",
        }

    treatment_values, control_values = _get_yield_values(
        connection,
        trial_id,
    )

    evidence_status = trial[6]

    result = {
        "trial_id": trial[0],
        "crop": trial[1],
        "product": trial[2],
        "country": trial[3],
        "year": trial[4],
        "trial_type": trial[5],
        "evidence_status": evidence_status,
        "found": True,
        "treatment_yield_kg_ha": None,
        "control_yield_kg_ha": None,
        "yield_difference_kg_ha": None,
        "yield_improvement_percent": None,
        "comparison_status": "not_comparable",
        "reason": None,
    }

    has_conflict = _has_issue(
        connection,
        trial_id,
        "conflict",
    )

    if has_conflict:
        result["comparison_status"] = "blocked"
        result["reason"] = (
            "Comparison is blocked because the trial "
            "contains conflicting evidence."
        )
        return result

    if len(treatment_values) == 0:
        result["reason"] = (
            "Treatment yield is missing."
        )
        return result

    if len(control_values) == 0:
        result["treatment_yield_kg_ha"] = (
            _decimal_to_string(
                treatment_values[0]
            )
        )
        result["comparison_status"] = "incomplete"
        result["reason"] = (
            "Control yield is missing."
        )
        return result

    if len(set(treatment_values)) > 1:
        result["comparison_status"] = "blocked"
        result["reason"] = (
            "Multiple treatment yield values exist."
        )
        return result

    if len(set(control_values)) > 1:
        result["comparison_status"] = "blocked"
        result["reason"] = (
            "Multiple control yield values exist."
        )
        return result

    treatment = treatment_values[0]
    control = control_values[0]

    result["treatment_yield_kg_ha"] = (
        _decimal_to_string(
            treatment
        )
    )

    result["control_yield_kg_ha"] = (
        _decimal_to_string(
            control
        )
    )

    difference = treatment - control

    result["yield_difference_kg_ha"] = (
        _decimal_to_string(
            difference
        )
    )

    if control == 0:
        result["comparison_status"] = "blocked"
        result["reason"] = (
            "Percentage improvement cannot be calculated "
            "because control yield is zero."
        )
        return result

    improvement = (
        difference
        / control
        * Decimal("100")
    )

    result["yield_improvement_percent"] = str(
        improvement.quantize(
            Decimal("0.01")
        )
    )

    result["comparison_status"] = "comparable"

    return result


def compare_trials(
    connection: sqlite3.Connection,
    trial_ids: list[str],
) -> dict:
    """
    Compare treatment and control yields for requested trials.

    Calculations are performed only when the underlying evidence
    is sufficiently consistent and complete.

    Conflicting or incomplete trials are returned with an explicit
    comparison status rather than a fabricated calculation.
    """

    if not trial_ids:
        return {
            "trials": [],
            "count": 0,
        }

    comparisons = [
        _comparison_for_trial(
            connection,
            trial_id,
        )
        for trial_id in trial_ids
    ]

    return {
        "trials": comparisons,
        "count": len(comparisons),
    }