"""Records billable/measurable events to the append-only `usage_records`
ledger — the data source for the analytics dashboard (`analytics_service.py`)
and any future usage-based billing.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import UsageEventType, UsageRecord

# Approximate list pricing, USD per 1M tokens, input/output. Not exact: this
# ignores prompt-cache discounts (~0.1x read, ~1.25x write) and any
# organization-specific pricing agreement — good enough for a relative-cost
# dashboard, not for an invoice. Update alongside shared/models.md upstream.
_LLM_PRICING_PER_MILLION: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.00, 50.00),
    "claude-mythos-5": (10.00, 50.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-opus-4-5": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def estimate_llm_cost_usd(*, model: str, tokens_input: int, tokens_output: int) -> float:
    input_rate, output_rate = _LLM_PRICING_PER_MILLION.get(model, (0.0, 0.0))
    return (tokens_input / 1_000_000) * input_rate + (tokens_output / 1_000_000) * output_rate


@dataclass(frozen=True, slots=True)
class UsageContext:
    """Bundles the tenant-scoping fields every usage record needs, so call
    sites don't have to repeat all three."""

    organization_id: uuid.UUID
    workspace_id: uuid.UUID | None
    user_id: uuid.UUID | None


async def record_usage(
    db: AsyncSession,
    *,
    context: UsageContext,
    event_type: UsageEventType,
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost_usd: float = 0.0,
    metadata: dict | None = None,
) -> UsageRecord:
    record = UsageRecord(
        organization_id=context.organization_id,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        event_type=event_type.value,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost_usd=cost_usd,
        usage_metadata=metadata or {},
    )
    db.add(record)
    await db.flush()
    return record
