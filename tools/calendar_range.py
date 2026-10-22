"""Print the UTC query bounds for the twelve displayed calendar months."""

from datetime import UTC, datetime


def calendar_range(now: datetime) -> tuple[str, str]:
    end = now.astimezone(UTC)
    first_month = end.year * 12 + end.month - 1 - 11
    year, month = divmod(first_month, 12)
    start = datetime(year, month + 1, 1, tzinfo=UTC)
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


if __name__ == "__main__":
    print(*calendar_range(datetime.now(UTC)))
