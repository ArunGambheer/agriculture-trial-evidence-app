import sqlite3

from agent.agent import AgriculturalTrialAgent
from database.schema import create_database


class FakeResponse:
    def __init__(self, text=None, function_calls=None):
        self.text = text
        self.function_calls = function_calls or []
        self.candidates = []


class FakeFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class FakeModels:
    def __init__(self):
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1

        if self.calls == 1:
            return FakeResponse(
                function_calls=[
                    FakeFunctionCall(
                        "search_trials",
                        {"crop": "wheat"},
                    )
                ]
            )

        return FakeResponse(
            text="I found the requested wheat trials."
        )


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def build_test_database():
    connection = create_database(":memory:")

    connection.execute(
        """
        INSERT INTO trials (
            trial_id,
            crop,
            product,
            country,
            year,
            trial_type,
            evidence_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "TEST01",
            "wheat",
            "Harvest Plus",
            "DE",
            2024,
            "Scientific",
            "consistent",
        ),
    )

    connection.commit()

    return connection


def test_agent_executes_tool_and_returns_final_answer():
    connection = build_test_database()

    agent = AgriculturalTrialAgent(
        connection=connection,
        client=FakeClient(),
    )

    answer = agent.answer(
        "Show me the wheat trials."
    )

    assert answer == (
        "I found the requested wheat trials."
    )

    assert agent.client.models.calls == 2

    connection.close()