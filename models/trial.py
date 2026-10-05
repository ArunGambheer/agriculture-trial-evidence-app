from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TrialObservation(BaseModel):
    """
    Canonical representation of one observation extracted from a source.

    This model represents a source observation, not necessarily a unique
    trial in the final database. Multiple observations can belong to the
    same trial_id when the same trial appears in multiple sources.
    """

    model_config = ConfigDict(extra="forbid")

    trial_id: str = Field(min_length=1)
    crop: str = Field(min_length=1)
    product: str = Field(min_length=1)
    country: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    trial_type: str = Field(min_length=1)

    treatment_yield_kg_ha: Optional[Decimal] = Field(
        default=None,
        ge=0,
    )

    control_yield_kg_ha: Optional[Decimal] = Field(
        default=None,
        ge=0,
    )

    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)