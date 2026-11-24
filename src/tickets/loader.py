import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .model import Ticket

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InvalidRow:
    row_number: int
    row: dict[str, str | None]
    errors: str


@dataclass(frozen=True)
class LoadResult:
    valid: list[Ticket]
    invalid: list[InvalidRow]


REQUIRED_COLUMNS = {
    "ticket_id",
    "customer_name",
    "service_date",
    "service_type",
    "status",
}


def load_csv(path: str | Path) -> LoadResult:
    """Load and validate every row in a ticket CSV."""
    csv_path = Path(path)

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    valid: list[Ticket] = []
    invalid: list[InvalidRow] = []

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = set(reader.fieldnames or [])

        missing = sorted(REQUIRED_COLUMNS - fieldnames)
        if missing:
            message = f"missing required columns: {', '.join(missing)}"
            logger.error("%s", message)
            raise ValueError(message)

        for row_number, row in enumerate(reader, start=2):
            try:
                ticket = Ticket.model_validate(row)
            except ValidationError as exc:
                errors = "; ".join(
                    f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                    for error in exc.errors()
                )
                invalid.append(InvalidRow(row_number, row, errors))
                logger.warning("Invalid row %d: %s", row_number, errors)
            else:
                valid.append(ticket)
                logger.info("Valid row %d: ticket_id=%s", row_number, ticket.ticket_id)

    logger.info("Loaded %d valid and %d invalid rows", len(valid), len(invalid))
    return LoadResult(valid=valid, invalid=invalid)
