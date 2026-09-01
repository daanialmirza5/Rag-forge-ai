from datetime import date

from pydantic import BaseModel


class UsageDailyPointRead(BaseModel):
    day: date
    event_type: str
    event_count: int
    tokens_input: int
    tokens_output: int
    cost_usd: float


class UsageSummaryRead(BaseModel):
    points: list[UsageDailyPointRead]
    total_events: int
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
