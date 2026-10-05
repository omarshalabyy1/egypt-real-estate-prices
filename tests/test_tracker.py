"""Checks for the parts that break when the site changes its pages: run with `pytest`. The
price_change check needs the warehouse (docker compose up -d warehouse, WAREHOUSE_PASSWORD set)."""

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import tracker

PAGES = Path(__file__).parent / "pages"
UNIT_URL = "https://realestate.eg/en/12324-pent-house-for-sale-in-the-square-new-cairo-from-170-meter"


def test_index_page():
    url = "https://realestate.eg/en/listings/new-cairo?location=8&page=1"
    cards, has_next = tracker.parse_index((PAGES / "new-cairo-page-1.html").read_bytes(), url)
    assert len(cards) == 50
    assert sum(not c["is_project"] for c in cards) == 48
    assert has_next
    first_unit = next(c for c in cards if not c["is_project"])
    assert first_unit == {
        "listing_id": 5063208,
        "url": "https://realestate.eg/en/5063208-apartments-for-sale-in-the-red-residence-fifth-settlement-learn-more-and-buy-now",
        "area_id": "new-cairo",
        "unit_type": "Apartment",
        "compound": "The Red Residence Compound New Cairo Al Borouj Misr Development",
        "bedrooms": 4,
        "bathrooms": 2,
        "size_m2": Decimal("170"),
        "is_project": False,
    }


def test_empty_index_page_fails_loudly():
    with pytest.raises(RuntimeError):
        tracker.parse_index(b"<html><body></body></html>", "https://realestate.eg/en/listings/new-cairo?location=8&page=1")


def test_unit_page():
    assert tracker.parse_unit((PAGES / "unit-12324.html").read_bytes(), UNIT_URL) == {
        "asking_price": Decimal("13600000"),
        "size_m2": Decimal("170"),
        "price_per_m2": Decimal("80000.00"),
        "bedrooms": 3,
        "bathrooms": 3,
        "compound": "The Square New Cairo Compound Al Ahly Sabbour Developments",
        "developer": "Al Ahly Sabbour developments",
    }


def test_unit_page_without_json_ld():
    soup = BeautifulSoup((PAGES / "unit-12324.html").read_bytes(), "html.parser")
    for script in soup.select('script[type="application/ld+json"]'):
        script.decompose()
    assert tracker.parse_unit(str(soup), UNIT_URL) is None


def test_run_week_starts_on_sunday():
    assert tracker.run_week_of(date(2026, 10, 7)) == date(2026, 10, 4)   # a Wednesday
    assert tracker.run_week_of(date(2026, 10, 4)) == date(2026, 10, 4)   # a Sunday
    assert tracker.run_week_of(date(2026, 10, 10)) == date(2026, 10, 4)  # a Saturday


@pytest.mark.skipif(not os.environ.get("WAREHOUSE_PASSWORD"), reason="needs the warehouse: set WAREHOUSE_PASSWORD")
def test_price_change_catches_cuts_and_rises():
    """Two weeks of prices for three test listings: a cut, a rise and an unchanged price. Everything
    runs in one transaction that is rolled back, so the warehouse is left as it was."""
    conn = tracker.connect()
    try:
        conn.execute((tracker.ROOT / "sql" / "schema.sql").read_text())
        conn.execute("INSERT INTO area VALUES ('test-area', 'Test area', -1)")
        for listing_id in (-1, -2, -3):
            conn.execute(
                "INSERT INTO listing (listing_id, url, area_id, unit_type, size_m2, first_seen, last_seen)"
                " VALUES (%s, 'test', 'test-area', 'Apartment', 100, '2026-09-28', '2026-10-05')", (listing_id,))
        for listing_id, old, new in ((-1, 5000000, 4500000), (-2, 5000000, 5250000), (-3, 5000000, 5000000)):
            for day, week, price in (("2026-09-28", "2026-09-27", old), ("2026-10-05", "2026-10-04", new)):
                conn.execute(
                    "INSERT INTO price_observation VALUES (%s, %s, %s, %s / 100.0, %s, %s)",
                    (listing_id, day, price, price, datetime.now(timezone.utc), week))
        changes = conn.execute(
            "SELECT listing_id, old_price, new_price, change_pct, caught_week, is_cut FROM price_change"
            " WHERE listing_id < 0 ORDER BY listing_id DESC").fetchall()
        assert changes == [
            (-1, Decimal("5000000.00"), Decimal("4500000.00"), Decimal("-10.0"), date(2026, 10, 4), True),
            (-2, Decimal("5000000.00"), Decimal("5250000.00"), Decimal("5.0"), date(2026, 10, 4), False),
        ]
    finally:
        conn.rollback()
        conn.close()


@pytest.mark.skipif(not os.environ.get("WAREHOUSE_PASSWORD"), reason="needs the warehouse: set WAREHOUSE_PASSWORD")
def test_rejected_row_goes_to_quarantine_once():
    """A rejected card is kept with its reason and what was read; saving it again adds nothing."""
    conn = tracker.connect()
    try:
        conn.execute((tracker.ROOT / "sql" / "schema.sql").read_text())
        card = {"listing_id": None, "url": "test-url", "size_m2": Decimal("170.5")}
        rejected = tracker.reject("test-url", datetime.now(timezone.utc), "unparseable id", card)
        for _ in range(2):
            tracker.save(conn, [], [rejected], date(2026, 10, 4))
        assert conn.execute("SELECT reason, payload->>'size_m2' FROM quarantine WHERE url = 'test-url'").fetchall() == [
            ("unparseable id", "170.5")
        ]
    finally:
        conn.rollback()
        conn.close()


class FakeResponse:
    content, url = b"", "https://realestate.eg/en/listings/test"

    def raise_for_status(self):
        pass


@pytest.mark.parametrize("residential, has_next, pages_read, cards_kept", [
    (50, True, 3, 150),  # 150 residential cards reached on page 3
    (7, True, 8, 56),    # mostly offices: stops at the 8-page cap
    (50, False, 1, 50),  # the area has one page
])
def test_index_pages_read_until_150_units_or_8_pages(monkeypatch, residential, has_next, pages_read, cards_kept):
    """Fake index pages of 50 cards, `residential` of them apartments and the rest offices."""
    fetched = []
    monkeypatch.setattr(tracker, "fetch", lambda robots, url, name: (fetched.append(url) or FakeResponse(), None))
    page = [{"listing_id": i, "url": "", "area_id": "test-area", "is_project": False,
             "unit_type": "Apartment" if i < residential else "Office"} for i in range(50)]
    monkeypatch.setattr(tracker, "parse_index", lambda html, url: (page, has_next))
    counts = tracker.Counter()
    cards = tracker.read_cards(None, "test-area", -1, {"test-area"}, counts, [])
    assert (len(fetched), len(cards)) == (pages_read, cards_kept)
    assert counts["non-residential cards skipped"] == pages_read * (50 - residential)


def test_unit_page_without_developer_keeps_the_key(monkeypatch):
    """save() needs every key: a unit page naming no developer gives developer None, not a missing key."""
    FakeResponse.status_code = 200
    monkeypatch.setattr(tracker, "fetch", lambda robots, url, name: (FakeResponse(), datetime.now(timezone.utc)))
    monkeypatch.setattr(tracker, "parse_unit", lambda html, url: {
        "asking_price": Decimal("5000000"), "size_m2": Decimal("100"), "price_per_m2": Decimal("50000.00"),
        "bedrooms": 3, "bathrooms": 2, "compound": "Test", "developer": None})
    card = {"listing_id": 1, "url": "test", "area_id": "test-area", "unit_type": "Apartment", "compound": "Test",
            "bedrooms": 3, "bathrooms": 2, "size_m2": Decimal("100"), "is_project": False}
    units = tracker.read_units(None, [card], tracker.Counter(), [])
    assert units[0]["developer"] is None

@pytest.mark.skipif(not os.environ.get("WAREHOUSE_PASSWORD"), reason="needs the warehouse: set WAREHOUSE_PASSWORD")
def test_benchmarks_count_only_the_latest_run():
    """A listing missing from the latest run leaves the benchmarks but stays in latest_price. Rolled back."""
    conn = tracker.connect()
    try:
        conn.execute((tracker.ROOT / "sql" / "schema.sql").read_text())
        conn.execute("INSERT INTO area VALUES ('test-area', 'Test area', -1)")
        conn.execute("INSERT INTO our_unit (unit_code, area_id, compound, unit_type, bedrooms, size_m2, asking_price)"
                     " VALUES ('test-unit', 'test-area', 'Test', 'Apartment', 3, 100, 5000000)")
        for listing_id, day, week in ((-1, "2000-01-03", "2000-01-02"), (-2, "2099-01-05", "2099-01-04")):
            conn.execute(
                "INSERT INTO listing (listing_id, url, area_id, compound, unit_type, size_m2, first_seen, last_seen)"
                " VALUES (%s, 'test', 'test-area', 'Test', 'Apartment', 100, %s, %s)", (listing_id, day, day))
            conn.execute("INSERT INTO price_observation VALUES (%s, %s, 5000000, 50000, %s, %s)",
                         (listing_id, day, datetime.now(timezone.utc), week))
        assert conn.execute(
            "SELECT (SELECT listings FROM area_benchmark WHERE area_id = 'test-area'),"
            " (SELECT listings FROM compound_benchmark WHERE area_id = 'test-area'),"
            " (SELECT listings_compared FROM unit_gap WHERE unit_code = 'test-unit'),"
            " (SELECT count(*) FROM latest_price WHERE area_id = 'test-area')").fetchone() == (1, 1, 1, 2)
    finally:
        conn.rollback()
        conn.close()
