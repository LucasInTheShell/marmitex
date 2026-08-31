from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class OrderingWindow:
    scheduled_for: datetime
    cutoff_at: datetime

    def accepts(self, now: datetime) -> bool:
        return now < self.cutoff_at


def ordering_window(
    order_date: date,
    meal_time: time,
    lead_minutes: int,
    time_zone: str,
) -> OrderingWindow:
    if not 0 <= lead_minutes <= 1440:
        raise ValueError("lead_minutes must be between 0 and 1440")
    scheduled_for = datetime.combine(order_date, meal_time, ZoneInfo(time_zone))
    return OrderingWindow(
        scheduled_for=scheduled_for,
        cutoff_at=scheduled_for - timedelta(minutes=lead_minutes),
    )
