# Bootcamp-26-ai-studio

A starter repository for the Bootcamp 26 AI Studio. This repository currently
contains setup guidance; it does not yet include a runnable application.

## Requirements

- Python 3.12
- Git
- [uv](https://docs.astral.sh/uv/)

Check that the tools are available:

```bash
python --version
git --version
uv --version
```

## Local setup

Create a Python 3.12 virtual environment with uv:

```bash
uv venv --python 3.12
```

Activate it on Linux or macOS:

```bash
source .venv/bin/activate
```

On Windows PowerShell, use ` .venv\Scripts\Activate.ps1` instead.

Copy `.env.example` to `.env` and set any required local values there. Never
commit `.env` or put real credentials in `.env.example`.

There is no application entry point or dependency list yet, so there is not a
run command at this stage.

## Git workflow

Use a short-lived branch for each change, make focused commits, push the branch,
and open a pull request against `main`. Ask a teammate to review it, resolve
their feedback, and merge only after approval.

Commit messages use the Conventional Commits format, for example:

```text
docs: describe local setup
```

## Day 2: Ticket CSV validation

The `tickets` package provides a typed Pydantic `Ticket` model and a CSV loader.

```bash
uv sync --all-groups
uv run pytest -v
```

The loader reports valid tickets and row-specific validation errors. It logs valid and invalid rows with Python's `logging` module.

## Day 3: Synthetic vendor payments

All payment rows in this exercise are synthetic. Install the optional pandas
dependency and inspect the CSV:

```bash
uv sync --all-groups --extra analysis
uv run python scripts/explore_vendor_payments.py
```

With a local PostgreSQL server running and `createdb` available, create a
practice database and run the load, ten queries, and index-plan comparison
from the repository root:

```bash
createdb vendor_payments
psql -d vendor_payments -f queries.sql
```

The SQL uses `\copy` to load `vendor_payments.csv` from the current directory.
The load ignores payment IDs already present, so rerunning it does not duplicate
these sample rows. See [insights.md](insights.md) for the findings.