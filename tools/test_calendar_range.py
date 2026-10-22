import unittest
from datetime import UTC, datetime, timedelta, timezone

from calendar_range import calendar_range


class CalendarRangeTests(unittest.TestCase):
    def test_range_starts_with_the_first_of_the_twelve_displayed_months(self):
        cases = [
            ("2026-10-22T04:20:45", "2025-11-01T00:00:00+00:00"),
            ("2027-01-01T00:00:00", "2026-02-01T00:00:00+00:00"),
            ("2028-02-29T23:59:59", "2027-03-01T00:00:00+00:00"),
            ("2028-03-01T00:00:00", "2027-04-01T00:00:00+00:00"),
            ("2028-12-31T23:59:59", "2028-01-01T00:00:00+00:00"),
        ]
        for timestamp, expected_start in cases:
            with self.subTest(timestamp=timestamp):
                now = datetime.fromisoformat(timestamp).replace(tzinfo=UTC)
                start, end = calendar_range(now)
                self.assertEqual(start, expected_start)
                self.assertEqual(end, now.isoformat())

    def test_month_boundary_uses_utc(self):
        now = datetime(2027, 1, 1, 0, 30, tzinfo=timezone(timedelta(hours=9)))
        self.assertEqual(
            calendar_range(now),
            ("2026-01-01T00:00:00+00:00", "2026-12-31T15:30:00+00:00"),
        )


if __name__ == "__main__":
    unittest.main()
