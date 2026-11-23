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