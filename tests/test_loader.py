from pathlib import Path

import pytest

from tickets import load_csv


def write_csv(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "tickets.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_row(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ticket_id,customer_name,service_date,service_type,status\n"
        "A-001,Acme Office,2026-11-24,amc,open\n",
    )

    result = load_csv(path)

    assert len(result.valid) == 1
    assert result.valid[0].ticket_id == "A-001"
    assert result.invalid == []


def test_missing_field(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ticket_id,customer_name,service_date,service_type,status\n"
        "A-002,,2026-11-24,repair,open\n",
    )

    result = load_csv(path)

    assert result.valid == []
    assert len(result.invalid) == 1
    assert "customer_name" in result.invalid[0].errors


def test_bad_date(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ticket_id,customer_name,service_date,service_type,status\n"
        "A-003,Acme Office,24-11-2026,amc,open\n",
    )

    result = load_csv(path)

    assert len(result.invalid) == 1
    assert "service_date" in result.invalid[0].errors


def test_bad_enum(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ticket_id,customer_name,service_date,service_type,status\n"
        "A-004,Acme Office,2026-11-24,painting,open\n",
    )

    result = load_csv(path)

    assert len(result.invalid) == 1
    assert "service_type" in result.invalid[0].errors


def test_empty_file(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ticket_id,customer_name,service_date,service_type,status\n",
    )

    result = load_csv(path)

    assert result.valid == []
    assert result.invalid == []
