from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from .triager import DEFAULT_MODEL, TriageResult, triage_complaint

DEFAULT_SHEET = Path("accuracy.csv")
EXPECTED_FIELDS = ("equipment", "urgency", "hospital", "next_action")


def evaluate_sheet(
    client: anthropic.Anthropic,
    sheet_path: str | Path = DEFAULT_SHEET,
    *,
    model: str = DEFAULT_MODEL,
    prompt_version: str = "v2",
) -> tuple[int, int]:
    path = Path(sheet_path)
    with path.open(encoding="utf-8", newline="") as sheet_file:
        reader = csv.DictReader(sheet_file)
        required = {
            "sample_id",
            "complaint",
            *(f"expected_{field}" for field in EXPECTED_FIELDS),
        }
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"accuracy sheet is missing columns: {', '.join(missing)}")
        rows = list(reader)

    if len(rows) != 20:
        raise ValueError(f"accuracy sheet must contain 20 samples, found {len(rows)}")

    correct_count = 0
    for row in rows:
        result: TriageResult = triage_complaint(
            client,
            row["complaint"],
            model=model,
            prompt_version=prompt_version,
        )
        actual = result.model_dump(mode="json")
        is_correct = all(
            actual[field] == (row[f"expected_{field}"] or None)
            for field in EXPECTED_FIELDS
        )
        row.update(
            {
                f"{prompt_version}_actual_{field}": actual[field] or ""
                for field in EXPECTED_FIELDS
            }
        )
        row[f"{prompt_version}_correct"] = str(is_correct).lower()
        correct_count += is_correct

    fieldnames = [
        "sample_id",
        "complaint",
        *(f"expected_{field}" for field in EXPECTED_FIELDS),
        *(f"v1_actual_{field}" for field in EXPECTED_FIELDS),
        "v1_correct",
        *(f"v2_actual_{field}" for field in EXPECTED_FIELDS),
        "v2_correct",
    ]
    with path.open("w", encoding="utf-8", newline="") as sheet_file:
        writer = csv.DictWriter(sheet_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return correct_count, len(rows)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Run triage on the 20 accuracy samples and score exact matches."
    )
    parser.add_argument("--sheet", type=Path, default=DEFAULT_SHEET)
    parser.add_argument("--prompt-version", choices=("v1", "v2"), default="v2")
    parser.add_argument("--model", default=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL))
    args = parser.parse_args(argv)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "replace-me":
        print("Set ANTHROPIC_API_KEY in .env before evaluating.", file=sys.stderr)
        return 2

    client = anthropic.Anthropic(api_key=api_key, max_retries=5)
    try:
        correct, total = evaluate_sheet(
            client,
            args.sheet,
            model=args.model,
            prompt_version=args.prompt_version,
        )
    except (anthropic.APIError, OSError, ValueError) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Accuracy ({args.prompt_version}): "
        f"{correct}/{total} ({correct / total:.0%})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
