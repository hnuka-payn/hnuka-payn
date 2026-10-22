"""Turn anonymous daily contribution counts into the activity bookshelf."""

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "profile-template.svg"


@dataclass(frozen=True)
class Day:
    date: date
    count: int


def parse_days(payload: dict) -> tuple[Day, ...]:
    if payload.get("errors"):
        raise ValueError("GitHub returned an error; previous artwork is retained.")
    calendar = payload["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]
    days = []
    seen = set()
    for week in calendar["weeks"]:
        for item in week["contributionDays"]:
            day = date.fromisoformat(item["date"])
            count = item["contributionCount"]
            if type(count) is not int or count < 0:
                raise ValueError("Daily activity must be a nonnegative integer.")
            if day in seen:
                raise ValueError("Duplicate activity date.")
            seen.add(day)
            days.append(Day(day, count))
    if not days:
        raise ValueError("Expected at least one day of activity.")
    days.sort(key=lambda day: day.date)
    if any((right.date - left.date).days != 1 for left, right in pairwise(days)):
        raise ValueError("Activity dates must form a continuous calendar.")
    return tuple(days)


def month_levels(days: tuple[Day, ...]) -> list[tuple[str, float]]:
    last = days[-1].date
    end = last.year * 12 + last.month - 1
    totals = {ordinal: 0 for ordinal in range(end - 11, end + 1)}
    for day in days:
        ordinal = day.date.year * 12 + day.date.month - 1
        if ordinal in totals:
            totals[ordinal] += day.count
    peak = max(totals.values())
    return [
        (
            f"{ordinal // 12:04d}-{ordinal % 12 + 1:02d}",
            math.log1p(count) / math.log1p(peak) if peak else 0,
        )
        for ordinal, count in totals.items()
    ]


def element(tag, **attributes):
    return ET.Element(
        f"{{{NS}}}{tag}",
        {key.replace("_", "-"): str(value) for key, value in attributes.items()},
    )


def render(payload: dict, template: str, *, demo: bool = False) -> str:
    levels = month_levels(parse_days(payload))
    root = ET.fromstring(template)
    shelf = root.find(f".//{{{NS}}}svg[@id='activity-bookshelf']")
    if shelf is None:
        raise ValueError("The profile template must include an activity bookshelf.")
    records = [node for node in shelf if "data-month-index" in node.attrib]
    if len(records) != 12:
        raise ValueError("The activity bookshelf must contain twelve books.")
    for record, (month, strength) in zip(records, levels, strict=True):
        record.set("data-month", month)
        record.set("data-intensity", f"{strength:.3f}")
        height = 40 + strength * 79
        book = record.find(f"{{{NS}}}g")
        cover = book.find(f"{{{NS}}}rect")
        cover.set("y", str(229 - height))
        cover.set("height", str(height))
        cover.set("opacity", f"{0.35 + 0.65 * strength:.2f}")
        lines = book.findall(f"{{{NS}}}path")
        lines[0].set("d", f"M9.00,{238 - height:.2f}L9.00,218.00")
        lines[1].set("d", f"M18.00,{249 - height:.2f}L36.00,{249 - height:.2f}")
    if demo:
        label = element(
            "text",
            x=48,
            y=int(root.get("height")) - 24,
            fill="#526d73",
            font_size=16,
            font_family="sans-serif",
        )
        label.text = "デザイン見本 · 架空の活動データ"
        root.append(label)
    result = ET.tostring(root, encoding="unicode") + "\n"
    ET.fromstring(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    try:
        image = render(
            json.loads(args.input.read_text()),
            args.template.read_text(),
            demo=args.demo,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(image, encoding="utf-8")
    except (KeyError, TypeError, ValueError, OSError, ET.ParseError):
        print(
            "Activity artwork generation failed; previous image is retained.",
            file=sys.stderr,
        )
        return 1
    print(f"Generated {args.output.name}; daily activity is rendered as a bookshelf.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
