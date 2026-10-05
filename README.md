# Agricultural Trial Evidence App

A tool-using AI application for querying agricultural trial evidence from CSV files and text reports.

The application normalizes data from different sources, detects data-quality issues, stores source evidence in SQLite, and uses Gemini to answer natural-language questions through deterministic tools.

## Features

- Search trials by crop, product, country, year, and trial type
- Compare treatment and control yields
- Retrieve source-level evidence
- Detect duplicates, conflicts, missing values, and single-source evidence
- Preserve raw source content and normalized values
- Answer questions using Gemini function calling
- Streamlit and CLI interfaces

## Architecture

```text
CSV / TXT Sources
       |
       v
Ingestion
       |
       v
Normalization
       |
       v
Reconciliation / DQ
       |
       v
SQLite
       |
       v
Deterministic Tools
       |
       v
Gemini Agent
       |
       v
Streamlit / CLI
```

The LLM handles question understanding, tool selection, and response generation. Data retrieval, reconciliation, and numerical calculations are handled by deterministic application code.

## Tools

| Tool | Purpose |
|---|---|
| `search_trials` | Search trials using structured filters |
| `get_trial_evidence` | Retrieve source-level evidence |
| `compare_trials` | Calculate treatment/control differences |
| `find_data_quality_issues` | Retrieve data-quality issues |

## Project Structure

```text
agr/
├── agent/
├── data/
│   └── raw/
├── database/
├── reconciliation/
├── tools/
├── tests/
├── app.py
├── run_agent.py
├── requirements.txt
└── README.md
```

## Setup

### 1. Create virtual environment

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\\Scripts\\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Gemini

Create `.env`:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

### 4. Run Streamlit

```bash
streamlit run app.py
```

### CLI

```bash
python run_agent.py
```

## Example Questions

```text
Show all wheat trials involving Harvest Plus.

Compare the Harvest Plus wheat trials in France and Germany.

What evidence supports Root Boost improving potato yields?

What are the data-quality issues in T03?

What evidence is available for T06?

Can we claim that the treatment is statistically significant?
```

## Data Quality

The system preserves conflicting source values instead of silently choosing one.

For example, T03 contains different treatment yields in the supplied sources. The system records the conflict and blocks a definitive comparison.

Missing values and single-source evidence are also reported.

## Design Decisions

- **Deterministic calculations:** Yield comparisons are calculated by application tools, not the LLM.
- **Evidence preservation:** Source-level values and raw content are retained.
- **Conflict preservation:** Conflicting evidence is not silently resolved.
- **Single agent:** One Gemini agent is used with deterministic tools.
- **SQLite:** Used as the local evidence store for this prototype.

## Limitations

- Ingestion supports the supplied CSV and text report formats.
- SQLite is intended for this prototype.
- No authentication or production deployment is included.
- Gemini is required for natural-language agent responses.
- Statistical significance cannot be claimed when the supplied evidence does not support it.

## Testing

```bash
pytest
```

Tests cover ingestion, normalization, reconciliation, database loading, deterministic tools, and agent behavior.

## Scope

This is a time-boxed take-home prototype focused on:

- Evidence ingestion
- Normalization and reconciliation
- Provenance
- Deterministic analysis tools
- LLM tool calling
- Natural-language trial analysis
