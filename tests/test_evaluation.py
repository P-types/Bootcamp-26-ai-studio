import csv
from pathlib import Path

from tickets.evaluation import evaluate_sheet
from tickets.triager import TriageResult


def test_evaluate_sheet_scores_twenty_samples_and_handles_null_hospital(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "accuracy.csv"
    expected = {
        "equipment": "thermometer",
        "urgency": "low",
        "hospital": "",
        "next_action": "Log the cosmetic damage for routine inspection.",
    }
    with path.open("w", encoding="utf-8", newline="") as sheet_file:
        writer = csv.DictWriter(
            sheet_file,
            fieldnames=[
                "sample_id",
                "complaint",
                "expected_equipment",
                "expected_urgency",
                "expected_hospital",
                "expected_next_action",
                "v1_actual_equipment",
                "v1_actual_urgency",
                "v1_actual_hospital",
                "v1_actual_next_action",
                "v1_correct",
                "v2_actual_equipment",
                "v2_actual_urgency",
                "v2_actual_hospital",
                "v2_actual_next_action",
                "v2_correct",
            ],
        )
        writer.writeheader()
        for sample_id in range(1, 21):
            writer.writerow(
                {
                    "sample_id": sample_id,
                    "complaint": f"Thermometer casing is scratched, sample {sample_id}.",
                    **{f"expected_{key}": value for key, value in expected.items()},
                }
            )

    def fake_triage(*_args, **_kwargs) -> TriageResult:
        return TriageResult(
            equipment="thermometer",
            urgency="low",
            hospital=None,
            next_action="Log the cosmetic damage for routine inspection.",
        )

    monkeypatch.setattr("tickets.evaluation.triage_complaint", fake_triage)

    client = object()
    assert evaluate_sheet(
        client, path, prompt_version="v1"
    ) == (20, 20)  # type: ignore[arg-type]
    assert evaluate_sheet(
        client, path, prompt_version="v2"
    ) == (20, 20)  # type: ignore[arg-type]

    with path.open(encoding="utf-8", newline="") as sheet_file:
        rows = list(csv.DictReader(sheet_file))
    assert len(rows) == 20
    assert rows[0]["v1_actual_equipment"] == "thermometer"
    assert rows[0]["v1_correct"] == "true"
    assert rows[0]["v2_actual_hospital"] == ""
    assert rows[0]["v2_correct"] == "true"
