from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OperationalSettingsUpdate(BaseModel):
    order_cutoff_lead_minutes: int = Field(ge=0, le=1440)


class OperationalSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_cutoff_lead_minutes: int
    updated_at: datetime
