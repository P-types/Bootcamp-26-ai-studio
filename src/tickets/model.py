from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


class ServiceType(str, Enum):
    AMC = "amc"
    REPAIR = "repair"
    INSTALLATION = "installation"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Ticket(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ticket_id: str
    customer_name: str
    service_date: date
    service_type: ServiceType
    status: TicketStatus = TicketStatus.OPEN

    @field_validator("ticket_id", "customer_name")
    @classmethod
    def reject_empty_strings(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value
