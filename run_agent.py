from pathlib import Path

from agent.agent import AgriculturalTrialAgent
from data.ingestion import ingest_all_csvs
from data.report_ingestion import ingest_all_reports
from database.repository import (
    load_observations,
    load_raw_file_contents,
)
from database.schema import create_database
from reconciliation.quality import reconcile_all


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
DATABASE_PATH = BASE_DIR / "agricultural_trials.db"


def build_database():
    """
    Build the SQLite evidence database from the supplied raw sources.
    """

    csv_observations = ingest_all_csvs(RAW_DIR)
    report_observations = ingest_all_reports(RAW_DIR)

    observations = (
        csv_observations
        + report_observations
    )

    issues = reconcile_all(observations)

    raw_contents = load_raw_file_contents(
        RAW_DIR
    )

    connection = create_database(
        DATABASE_PATH
    )

    load_observations(
        connection=connection,
        observations=observations,
        issues=issues,
        raw_contents=raw_contents,
    )

    return connection


def main():
    print("Building agricultural trial evidence database...")

    connection = build_database()

    print(
        f"Database ready: {DATABASE_PATH}"
    )

    print(
        "Model: gemini-3.5-flash-lite"
    )

    agent = AgriculturalTrialAgent(
        connection=connection
    )

    print()
    print(
        "Ask an agricultural trial question."
    )
    print(
        "Type 'exit' to quit."
    )
    print()

    try:
        while True:
            question = input("You: ").strip()

            if question.lower() in {
                "exit",
                "quit",
            }:
                break

            if not question:
                continue

            try:
                answer = agent.answer(
                    question
                )

                print()
                print("Agent:")
                print(answer)
                print()

            except Exception as exc:
                print()
                print(
                    f"Agent error: {exc}"
                )
                print()

    finally:
        connection.close()


if __name__ == "__main__":
    main()