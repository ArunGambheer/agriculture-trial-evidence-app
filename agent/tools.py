from __future__ import annotations

from typing import Any


def get_tool_declarations() -> list[dict[str, Any]]:
    """
    Return the tool declarations exposed to the Gemini agent.

    These declarations describe the deterministic Python tools that
    Gemini is allowed to call. The actual implementations live in
    the `tools/` package.
    """

    return [
        {
            "name": "search_trials",
            "description": (
                "Search agricultural trials using optional structured filters. "
                "Use this tool to find trials by crop, product, country, year, "
                "or trial type. This tool returns canonical trial metadata and "
                "evidence status. Do not invent trial IDs."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "crop": {
                        "type": "STRING",
                        "description": (
                            "Canonical crop name, such as 'wheat' or 'potato'. "
                            "Use null or omit this field when no crop filter "
                            "is required."
                        ),
                    },
                    "product": {
                        "type": "STRING",
                        "description": (
                            "Canonical product name, such as 'Harvest Plus' "
                            "or 'Root Boost'."
                        ),
                    },
                    "country": {
                        "type": "STRING",
                        "description": (
                            "Canonical two-letter country code such as "
                            "'FR', 'DE', or 'ES'."
                        ),
                    },
                    "year": {
                        "type": "INTEGER",
                        "description": "Trial year.",
                    },
                    "trial_type": {
                        "type": "STRING",
                        "description": (
                            "Trial type, such as 'Scientific' or "
                            "'Demonstration'."
                        ),
                    },
                },
            },
        },
        {
            "name": "get_trial_evidence",
            "description": (
                "Retrieve the complete evidence package for a specific trial. "
                "Returns trial metadata, all contributing source documents, "
                "source-level yield values, normalized values, raw content "
                "when available, and data-quality issues. Use this when the "
                "user asks why a trial has a particular value or wants the "
                "underlying evidence."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "trial_id": {
                        "type": "STRING",
                        "description": (
                            "Exact canonical trial ID, such as 'T01' or 'T03'. "
                            "Only use IDs returned by search results or "
                            "explicitly provided by the user."
                        ),
                    },
                },
                "required": [
                    "trial_id",
                ],
            },
        },
        {
            "name": "find_data_quality_issues",
            "description": (
                "Find data-quality issues detected during deterministic "
                "reconciliation. Issues include duplicates, conflicts, "
                "missing values, and single-source evidence. Use this tool "
                "when the user asks about data quality, conflicting evidence, "
                "missing values, reliability, or caveats."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "trial_id": {
                        "type": "STRING",
                        "description": (
                            "Optional exact trial ID. Omit this field to "
                            "search across all trials."
                        ),
                    },
                    "issue_type": {
                        "type": "STRING",
                        "enum": [
                            "duplicate",
                            "conflict",
                            "missing_value",
                            "single_source",
                        ],
                        "description": (
                            "Optional data-quality issue type."
                        ),
                    },
                    "severity": {
                        "type": "STRING",
                        "enum": [
                            "info",
                            "warning",
                            "error",
                        ],
                        "description": (
                            "Optional issue severity."
                        ),
                    },
                },
            },
        },
        {
            "name": "compare_trials",
            "description": (
                "Compare treatment and control yields for one or more exact "
                "trial IDs. The deterministic backend calculates yield "
                "difference and percentage improvement. Comparisons are "
                "blocked when conflicting evidence makes the result unsafe "
                "to calculate, and incomplete when required values are "
                "missing. Never perform these calculations independently "
                "when this tool can provide the result."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "trial_ids": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING",
                        },
                        "description": (
                            "One or more exact canonical trial IDs, such as "
                            "['T01', 'T06']."
                        ),
                    },
                },
                "required": [
                    "trial_ids",
                ],
            },
        },
    ]