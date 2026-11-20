from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Device(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=120)
    capability: Literal["temperature.read", "mass.read_stable"]
    adapter: Literal["simulated"] = "simulated"


class Observation(StrictModel):
    event_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    device_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    experiment_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    value: FiniteFloat
    unit: Literal["degC", "g"]
    stable: bool = True
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value):
        if value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value


class Note(StrictModel):
    event_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    experiment_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    text: str = Field(min_length=1, max_length=10000)


class InventoryCalculation(StrictModel):
    gross_g: Decimal = Field(ge=0, allow_inf_nan=False, max_digits=18, decimal_places=6)
    tare_g: Decimal = Field(ge=0, allow_inf_nan=False, max_digits=18, decimal_places=6)
    density_g_ml: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False, max_digits=18, decimal_places=6)
    tare_kind: Literal["measured", "estimated"]
