from pathlib import Path
import sqlite3


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS trials (
    trial_id TEXT PRIMARY KEY,
    crop TEXT NOT NULL,
    product TEXT NOT NULL,
    country TEXT NOT NULL,
    year INTEGER NOT NULL,
    trial_type TEXT NOT NULL,
    evidence_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trial_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    raw_content TEXT,
    UNIQUE(trial_id, source_name),
    FOREIGN KEY (trial_id)
        REFERENCES trials(trial_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS source_results (
    source_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    raw_value TEXT,
    normalized_value TEXT,
    unit TEXT,
    UNIQUE(source_id, field_name),
    FOREIGN KEY (source_id)
        REFERENCES sources(source_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trial_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    field_name TEXT,
    description TEXT NOT NULL,
    source_names TEXT NOT NULL,
    FOREIGN KEY (trial_id)
        REFERENCES trials(trial_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_trials_crop
    ON trials(crop);

CREATE INDEX IF NOT EXISTS idx_trials_product
    ON trials(product);

CREATE INDEX IF NOT EXISTS idx_trials_country
    ON trials(country);

CREATE INDEX IF NOT EXISTS idx_trials_year
    ON trials(year);

CREATE INDEX IF NOT EXISTS idx_trials_trial_type
    ON trials(trial_type);

CREATE INDEX IF NOT EXISTS idx_source_results_source_id
    ON source_results(source_id);

CREATE INDEX IF NOT EXISTS idx_quality_issues_trial_id
    ON data_quality_issues(trial_id);
"""


def create_database(database_path: str | Path) -> sqlite3.Connection:
    """
    Create and initialize the SQLite database.

    The database schema is created if it does not already exist.
    """

    path = Path(database_path)

    if path.parent != Path("."):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    connection = sqlite3.connect(path, check_same_thread=False,)

    connection.execute("PRAGMA foreign_keys = ON")

    connection.executescript(SCHEMA_SQL)

    connection.commit()

    return connection