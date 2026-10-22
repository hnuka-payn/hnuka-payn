import copy
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

from generate import TEMPLATE, month_levels, parse_days, render


def calendar(count=3, *, start=date(2025, 10, 20), day_count=366):
    days = [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "contributionCount": count if i % 3 else 0,
        }
        for i in range(day_count)
    ]
    return {
        "data": {
            "user": {
                "contributionsCollection": {
                    "contributionCalendar": {"weeks": [{"contributionDays": days}]}
                }
            }
        }
    }


class ActivityArtTests(unittest.TestCase):
    def test_week_padded_calendar_renders_the_same_twelve_months(self):
        for day_count in (367, 368, 369, 371):
            with self.subTest(day_count=day_count):
                padded = calendar(start=date(2025, 10, 19), day_count=day_count)
                bounded = copy.deepcopy(padded)
                week = bounded["data"]["user"]["contributionsCollection"][
                    "contributionCalendar"
                ]["weeks"][0]
                week["contributionDays"] = [
                    day
                    for day in week["contributionDays"]
                    if day["date"] >= "2025-11-01"
                ]
                image = render(padded, TEMPLATE.read_text())
                self.assertEqual(image, render(bounded, TEMPLATE.read_text()))
                books = ET.fromstring(image).findall(".//*[@data-month]")
                self.assertEqual(len(books), 12)
                self.assertEqual(books[0].get("data-month"), "2025-11")
                self.assertEqual(books[-1].get("data-month"), "2026-10")

    def test_empty_and_incomplete_calendars_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_days(calendar(day_count=0))
        incomplete = calendar()
        incomplete["data"]["user"]["contributionsCollection"][
            "contributionCalendar"
        ]["weeks"][0]["contributionDays"].pop(10)
        with self.assertRaises(ValueError):
            parse_days(incomplete)

    def test_anonymous_private_counts_drive_art_without_publishing_details(self):
        data = calendar()
        collection = data["data"]["user"]["contributionsCollection"]
        collection["restrictedContributionsCount"] = 987654321
        collection["repository"] = {
            "name": "private-fixture-name",
            "organization": "private-fixture-org",
        }
        image = render(data, TEMPLATE.read_text())
        root = ET.fromstring(image)
        books = root.findall(".//*[@data-month]")
        self.assertEqual(len(books), 12)
        self.assertTrue(any(float(book.get("data-intensity")) > 0 for book in books))
        for term in [
            "private-fixture",
            "987654321",
            "PR作成",
            "コミット",
            "この1年",
            "コントリビューション",
        ]:
            self.assertNotIn(term, image)

    def test_zero_and_active_months_produce_different_books(self):
        quiet, active = calendar(0), calendar(8)
        self.assertNotEqual(
            render(quiet, TEMPLATE.read_text()), render(active, TEMPLATE.read_text())
        )
        self.assertTrue(all(level == 0 for _, level in month_levels(parse_days(quiet))))
        self.assertTrue(any(level > 0 for _, level in month_levels(parse_days(active))))
        root = ET.fromstring(render(quiet, TEMPLATE.read_text()))
        for book in root.findall(".//*[@data-month]"):
            cover = book.find(
                "{http://www.w3.org/2000/svg}g/{http://www.w3.org/2000/svg}rect"
            )
            self.assertEqual(float(cover.get("height")), 40)
            self.assertEqual(float(cover.get("opacity")), 0.35)

    def test_dates_change_which_books_grow(self):
        early, late = calendar(0), calendar(0)
        early["data"]["user"]["contributionsCollection"]["contributionCalendar"][
            "weeks"
        ][0]["contributionDays"][50]["contributionCount"] = 10
        late["data"]["user"]["contributionsCollection"]["contributionCalendar"][
            "weeks"
        ][0]["contributionDays"][300]["contributionCount"] = 10
        self.assertNotEqual(
            month_levels(parse_days(early)), month_levels(parse_days(late))
        )

    def test_months_cross_the_year_boundary_in_order(self):
        data = calendar(0)
        source = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        source["weeks"] = [
            {
                "contributionDays": [
                    {"date": "2025-12-30", "contributionCount": 0},
                    {"date": "2025-12-31", "contributionCount": 4},
                    {"date": "2026-01-01", "contributionCount": 1},
                ]
            }
        ]
        months = month_levels(parse_days(data))
        self.assertEqual(len(months), 12)
        self.assertEqual(months[0][0], "2025-02")
        self.assertEqual(months[-1][0], "2026-01")
        self.assertEqual(months[-2][1], 1)
        self.assertGreater(months[-1][1], 0)

    def test_activity_changes_only_the_bookshelf(self):
        namespace = {"s": "http://www.w3.org/2000/svg"}
        template = ET.parse(TEMPLATE).getroot()
        root = ET.fromstring(render(calendar(), TEMPLATE.read_text()))
        selector = ".//s:svg[@id='walk']"
        self.assertEqual(
            ET.tostring(template.find(selector, namespace)),
            ET.tostring(root.find(selector, namespace)),
        )
        self.assertIsNone(root.find(".//s:script", namespace))
        self.assertIn("prefers-reduced-motion", ET.tostring(root).decode())

    def test_large_counts_do_not_increase_the_artwork_node_count(self):
        counts = []
        for value in [100, 1_000, 10_000]:
            image = render(calendar(value), TEMPLATE.read_text())
            counts.append(len(list(ET.fromstring(image).iter())))
        self.assertEqual(len(set(counts)), 1)

    def test_bad_data_does_not_turn_into_a_false_quiet_calendar(self):
        with self.assertRaises(ValueError):
            parse_days({"errors": [{"message": "fixture error"}]})
        for value in [True, -1, "3"]:
            data = calendar()
            data["data"]["user"]["contributionsCollection"]["contributionCalendar"][
                "weeks"
            ][0]["contributionDays"][0]["contributionCount"] = value
            with self.assertRaises(ValueError):
                parse_days(data)
        data = calendar()
        source = data["data"]["user"]["contributionsCollection"][
            "contributionCalendar"
        ]["weeks"][0]["contributionDays"]
        source.append(copy.deepcopy(source[0]))
        with self.assertRaises(ValueError):
            parse_days(data)

    def test_failed_generation_retains_previous_art(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "input.json", Path(folder) / "profile.svg"
            source.write_text(json.dumps({"errors": [{"message": "fixture error"}]}))
            output.write_text("previous image")
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("generate.py")),
                    str(source),
                    str(output),
                ],
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "previous image")


if __name__ == "__main__":
    unittest.main()
