from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from app import swka
from app.feedv2.feed import Canteen, CanteenDay, generateFeedV2
from app.main import app

FIXTURE = (Path(__file__).parent / "fixtures" / "mensa_adenauerring_kw46.html").read_text(encoding="utf-8")
NS = {"om": "http://openmensa.org/open-mensa-v2"}


@pytest.fixture(scope="module")
def week():
    return swka.parseWeek(FIXTURE)


def test_days(week):
    assert list(week) == ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"]
    assert all(week.values())


def test_line_names(week):
    names = [c.name for c in week["2026-11-09"]]
    assert names[:3] == ["Linie 1 Gut & Günstig", "Linie 2 Vegane Linie", "Linie 3"]
    assert "[pizza]werk Pizza 11-14 Uhr" in names
    assert "Schnitzelbar" in names


def test_meal(week):
    linie1 = week["2026-11-09"][0]
    meal = linie1.meals[0]
    assert meal.name.startswith("Aubergine-Bulgur")
    assert meal.price == {"student": 3.60, "other": 5.20, "employee": 4.60, "pupil": 4.00}
    assert "enthält Geflügel" in meal.notes
    assert "Senf" in meal.notes and "Weizen" in meal.notes
    # entries without price become notes of the line's meals
    assert "zu jedem Gericht reichen wir ein Dessert, Salat oder Obst" in meal.notes
    assert all(m.price for m in linie1.meals)


def test_description_is_note(week):
    linie3 = next(c for c in week["2026-11-09"] if c.name == "Linie 3")
    salad = next(m for m in linie3.meals if m.name == "Blattsalat")
    assert "Gärtnerinsalat" in salad.notes


def test_every_meal_has_student_price(week):
    for cats in week.values():
        for c in cats:
            for m in c.meals:
                assert "student" in m.price, (c.name, m.name)


def test_feed_xml(week):
    days = [CanteenDay(d, cats) for d, cats in week.items()]
    xml = generateFeedV2(Canteen(days), "test")
    root = ET.fromstring(xml)
    assert len(root.findall("om:canteen/om:day", NS)) == 5
    assert root.find(".//om:price[@role='student']", NS).text == "3.60"


def test_get_canteen_filters_range_and_handles_errors(monkeypatch):
    def fake(canteen, week):
        if week == 46:
            return swka.parseWeek(FIXTURE)
        raise swka.UpstreamUnavailable("down")
    monkeypatch.setattr(swka, "fetchWeek", fake)
    canteen, errors = swka.getCanteen("mensa_adenauerring", date(2026, 11, 10), 14)
    assert [d.date for d in canteen.days] == ["2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"]
    assert len(errors) == 2


def test_endpoint_503_when_everything_fails(monkeypatch):
    def fake(canteen, week):
        raise swka.UpstreamUnavailable("down")
    monkeypatch.setattr(swka, "fetchWeek", fake)
    client = TestClient(app)
    assert client.get("/feed/adenauerring").status_code == 503
    assert client.get("/feed/adenauerring/2026-11-09").status_code == 503
    assert client.get("/feed/adenauerring/kaputt").status_code == 400
