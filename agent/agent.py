from __future__ import annotations

from typing import Any, Callable

from google import genai
from google.genai import types

from agent.config import get_model_name
from tools.search import search_trials
from tools.evidence import get_trial_evidence
from tools.quality import find_data_quality_issues
from tools.compare import compare_trials


MAX_TOOL_ITERATIONS = 8

EventCallback = Callable[[dict[str, Any]], None]


SYSTEM_INSTRUCTION = """
You are an evidence-first agricultural trial analysis agent.

Your job is to answer user questions about agricultural trial evidence using
the provided deterministic tools.

IMPORTANT PRINCIPLES:

1. NEVER invent trial IDs, yields, products, countries, years, or evidence.

2. ALWAYS use tools when the answer depends on trial data.

3. The deterministic tools are the source of truth for:
   - trial discovery
   - filtering
   - comparisons
   - evidence retrieval
   - data-quality issues
   - numerical calculations
   - conflicts

4. Do not perform numerical calculations yourself when a comparison tool
   can perform them.

5. If evidence conflicts across sources:
   - explicitly identify the conflict
   - show the competing values
   - identify the sources when available
   - do not silently choose one value
   - do not claim a definitive result unless the evidence supports it

6. If required evidence is missing:
   - clearly state what is missing
   - do not infer or fabricate it

7. Distinguish between:
   - supported evidence
   - inference
   - missing evidence
   - conflicting evidence

8. Be especially careful with:
   - units such as t/ha and kg/ha
   - product name variants
   - crop name variants
   - country codes
   - trial type capitalization
   - duplicate observations

9. When the user asks a broad question, start with search_trials.

10. When the user asks about a specific trial, use get_trial_evidence.

11. When the user asks about data quality, use find_data_quality_issues.

12. When the user asks to compare trials, use compare_trials.

13. You may call multiple tools when needed. Use the result of one tool
    to decide what to do next.

14. Do not claim statistical significance unless the evidence explicitly
    supports it.

15. Keep answers concise but sufficiently explain the evidence and any
    important caveats.

16. If no matching evidence exists, clearly say that no matching evidence
    was found.

17. Do not expose hidden reasoning or chain-of-thought. Provide only the
    conclusions, evidence, calculations, and relevant tool activity.
"""


def _tool_registry(connection) -> dict[str, Callable[..., Any]]:
    return {
        "search_trials": lambda **kwargs: search_trials(
            connection=connection,
            **kwargs,
        ),
        "get_trial_evidence": lambda **kwargs: get_trial_evidence(
            connection=connection,
            **kwargs,
        ),
        "find_data_quality_issues": lambda **kwargs: find_data_quality_issues(
            connection=connection,
            **kwargs,
        ),
        "compare_trials": lambda **kwargs: compare_trials(
            connection=connection,
            **kwargs,
        ),
    }


def _build_gemini_tools() -> list[types.Tool]:
    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="search_trials",
                    description=(
                        "Search agricultural trials using optional filters "
                        "such as crop, product, country, year, or trial type."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "crop": types.Schema(
                                type=types.Type.STRING,
                                description="Crop name, for example Wheat or Potato.",
                            ),
                            "product": types.Schema(
                                type=types.Type.STRING,
                                description="Product name, for example Harvest Plus or RootBoost.",
                            ),
                            "country": types.Schema(
                                type=types.Type.STRING,
                                description="Country name or country code, for example France or FR.",
                            ),
                            "year": types.Schema(
                                type=types.Type.INTEGER,
                                description="Trial year.",
                            ),
                            "trial_type": types.Schema(
                                type=types.Type.STRING,
                                description="Trial type, for example Scientific or Demonstration.",
                            ),
                        },
                    ),
                ),
                types.FunctionDeclaration(
                    name="get_trial_evidence",
                    description=(
                        "Retrieve detailed evidence and provenance for a specific "
                        "agricultural trial."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "trial_id": types.Schema(
                                type=types.Type.STRING,
                                description="Trial identifier such as T01 or T03.",
                            ),
                        },
                        required=["trial_id"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="find_data_quality_issues",
                    description=(
                        "Find data-quality issues for agricultural trials, optionally "
                        "filtered by trial ID, issue type, or severity."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "trial_id": types.Schema(
                                type=types.Type.STRING,
                                description="Optional trial identifier.",
                            ),
                            "issue_type": types.Schema(
                                type=types.Type.STRING,
                                description=(
                                    "Optional issue type such as conflict, "
                                    "missing_value, duplicate, or single_source."
                                ),
                            ),
                            "severity": types.Schema(
                                type=types.Type.STRING,
                                description="Optional severity such as low, medium, or high.",
                            ),
                        },
                    ),
                ),
                types.FunctionDeclaration(
                    name="compare_trials",
                    description=(
                        "Compare two or more agricultural trials and calculate "
                        "treatment-versus-control differences where possible."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "trial_ids": types.Schema(
                                type=types.Type.ARRAY,
                                items=types.Schema(type=types.Type.STRING),
                                description="List of trial IDs to compare.",
                            ),
                        },
                        required=["trial_ids"],
                    ),
                ),
            ]
        )
    ]


def _serialize_tool_result(result: Any) -> Any:
    if result is None:
        return None

    if isinstance(result, (str, int, float, bool)):
        return result

    if isinstance(result, dict):
        return {
            str(key): _serialize_tool_result(value)
            for key, value in result.items()
        }

    if isinstance(result, (list, tuple)):
        return [_serialize_tool_result(item) for item in result]

    return str(result)


def _execute_tool(
    registry: dict[str, Callable[..., Any]],
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:

    if tool_name not in registry:
        return {
            "error": f"Unknown tool requested: {tool_name}"
        }

    try:
        result = registry[tool_name](**arguments)
        return _serialize_tool_result(result)

    except Exception as exc:
        return {
            "error": f"Tool execution failed: {str(exc)}"
        }


class AgriculturalTrialAgent:

    def __init__(self, connection):

        # Keep the existing project interface:
        # AgriculturalTrialAgent(connection=connection)
        self.client = genai.Client()

        self.connection = connection
        self.model_name = get_model_name()

        self._tools = _build_gemini_tools()
        self._registry = _tool_registry(connection)

        self.last_trace: list[dict[str, Any]] = []

        # Possible states:
        # idle -> running -> completed
        # idle -> running -> failed
        self.last_status = "idle"

    def _emit_event(
        self,
        on_event: EventCallback | None,
        event: dict[str, Any],
    ) -> None:

        if on_event is None:
            return

        try:
            on_event(event)
        except Exception:
            # UI callback failures must never break the agent.
            pass

    def answer(
        self,
        question: str,
        on_event: EventCallback | None = None,
    ) -> str:

        self.last_trace = []
        self.last_status = "running"

        self._emit_event(
            on_event,
            {
                "type": "agent_started",
                "question": question,
                "model": self.model_name,
            },
        )

        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=question)
                ],
            )
        ]

        try:

            for iteration in range(MAX_TOOL_ITERATIONS):

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=self._tools,
                    ),
                )

                candidate = response.candidates[0]

                function_calls = []

                if candidate.content and candidate.content.parts:

                    for part in candidate.content.parts:

                        if part.function_call is not None:
                            function_calls.append(part.function_call)

                # ---------------------------------------------------------
                # Gemini has finished and returned a normal answer.
                # ---------------------------------------------------------

                if not function_calls:

                    final_text = response.text or ""

                    self.last_status = "completed"

                    self._emit_event(
                        on_event,
                        {
                            "type": "agent_completed",
                            "answer": final_text,
                            "trace": self.last_trace,
                        },
                    )

                    return final_text

                # Preserve Gemini's function-call message.
                contents.append(candidate.content)

                tool_response_parts: list[types.Part] = []

                # ---------------------------------------------------------
                # Execute requested tools.
                # ---------------------------------------------------------

                for function_call in function_calls:

                    tool_name = function_call.name or ""

                    raw_arguments = function_call.args or {}

                    arguments = dict(raw_arguments)

                    step_number = len(self.last_trace) + 1

                    # Live event: tool is about to execute.
                    self._emit_event(
                        on_event,
                        {
                            "type": "tool_started",
                            "step": step_number,
                            "iteration": iteration + 1,
                            "tool": tool_name,
                            "arguments": arguments,
                        },
                    )

                    # Actual deterministic tool execution.
                    tool_result = _execute_tool(
                        self._registry,
                        tool_name,
                        arguments,
                    )

                    trace_entry = {
                        "step": step_number,
                        "iteration": iteration + 1,
                        "type": "tool_call",
                        "tool": tool_name,
                        "arguments": arguments,
                        "result": tool_result,
                    }

                    self.last_trace.append(trace_entry)

                    # Live event: tool finished.
                    self._emit_event(
                        on_event,
                        {
                            "type": "tool_completed",
                            "step": step_number,
                            "iteration": iteration + 1,
                            "tool": tool_name,
                            "arguments": arguments,
                            "result": tool_result,
                        },
                    )

                    # Gemini function response.
                    function_response = types.FunctionResponse(
                        name=tool_name,
                        response={
                            "result": tool_result
                        },
                    )

                    tool_response_parts.append(
                        types.Part(
                            function_response=function_response
                        )
                    )

                # Send tool results back to Gemini.
                contents.append(
                    types.Content(
                        role="user",
                        parts=tool_response_parts,
                    )
                )

            # -------------------------------------------------------------
            # Maximum iterations reached.
            # -------------------------------------------------------------

            self.last_status = "failed"

            error_message = (
                "The agent reached the maximum number of tool iterations "
                f"({MAX_TOOL_ITERATIONS}) without producing a final answer."
            )

            self._emit_event(
                on_event,
                {
                    "type": "agent_failed",
                    "error": error_message,
                    "trace": self.last_trace,
                },
            )

            return error_message

        except Exception as exc:

            self.last_status = "failed"

            self._emit_event(
                on_event,
                {
                    "type": "agent_failed",
                    "error": str(exc),
                    "trace": self.last_trace,
                },
            )

            raise