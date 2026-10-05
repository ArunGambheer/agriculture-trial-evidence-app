from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class IssueType(str, Enum):
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    MISSING_VALUE = "missing_value"
    SINGLE_SOURCE = "single_source"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DataQualityIssue(BaseModel):
    """
    Represents a deterministic data-quality finding for a logical trial.
    """

    model_config = ConfigDict(extra="forbid")

    trial_id: str = Field(min_length=1)
    issue_type: IssueType
    severity: Severity
    field_name: Optional[str] = None
    description: str = Field(min_length=1)

    source_names: list[str] = Field(default_factory=list)