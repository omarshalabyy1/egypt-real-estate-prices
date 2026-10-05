"""Checks for realestate.eg's pages, the extract's stopping rules and watermark, the row checks and
their reconciliation, and gold: run with `pytest`. The warehouse checks need the warehouse (docker
compose up -d warehouse, WAREHOUSE_PASSWORD set); each runs in a transaction that is rolled back."""

import os
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from bs4 import BeautifulSoup

import sites
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


def test_page_names():
    assert tracker.page_name("https://realestate.eg/en/listings/new-cairo?location=8&page=3") == "new-cairo-page-3"
    assert tracker.page_name(UNIT_URL) == "12324"


def row(listing_id, area="new-cairo", unit_type="Apartment", price=Decimal("5000000"), size=Decimal("100")):
    return {**sites.row("nawy", listing_id, f"u{listing_id}", area, None, None, unit_type, 3, 2, size, price, None),
            "fetched_at": "2026-10-05T00:00:00+00:00"}


def test_every_row_is_counted_once_and_reconciles():
    rows = [row(1), row(2, area=None), row(3, unit_type="Office"), row(1), row(4, unit_type="Igloo"),
            row(5, price=None), row(6, size=None), row(7), row(8)]
    counts, saved, rejected = tracker.check(rows, set(), {("nawy", "8"): "no JSON-LD"})
    assert counts == Counter(parsed=9, skipped=2, duplicate=1, saved=2, quarantined=4)
    assert [r["source_listing_id"] for r in saved] == ["1", "7"]
    assert [reason for reason, _ in rejected] == ["unknown type", "price missing or <= 0", "size missing or <= 0",
                                                  "no JSON-LD"]
    tracker.reconcile(counts, "test")


def test_a_type_the_client_does_not_compare_is_skipped_not_quarantined(monkeypatch):
    monkeypatch.setattr(sites, "NOT_COMPARED", {"Villa"})
    counts, saved, rejected = tracker.check([row(1, unit_type="Villa"), row(2)], set(), {})
    assert counts == Counter(parsed=2, skipped=1, saved=1) and not rejected


def test_ivilla_cabin_and_loft_are_saved_and_a_building_is_skipped():
    rows = [row(1, unit_type=sites.unit_type("iVilla")), row(2, unit_type=sites.unit_type("Cabin")),
            row(3, unit_type=sites.unit_type("Loft")), row(4, unit_type=sites.unit_type("Building"))]
    counts, saved, _ = tracker.check(rows, set(), {})
    assert counts == Counter(parsed=4, saved=3, skipped=1)
    assert [r["unit_type"] for r in saved] == ["iVilla", "Cabin", "Loft"]


def test_a_listing_seen_in_an_earlier_area_is_a_duplicate():
    seen = set()
    tracker.check([row(1)], seen, {})
    assert tracker.check([row(1, area="mostakbal-city")], seen, {})[0]["duplicate"] == 1


@pytest.mark.parametrize("price, quarantined", [
    (Decimal("999999"), True),     # 9,999.99 per m²
    (Decimal("1000000"), False),   # 10,000 per m²
    (Decimal("40000000"), False),  # 400,000 per m²
    (Decimal("40000001"), True),   # 400,000.01 per m²
])
def test_a_price_per_m2_outside_10000_to_400000_is_quarantined(price, quarantined):
    counts, saved, rejected = tracker.check([row(1, price=price, size=Decimal("100"))], set(), {})
    assert [reason for reason, _ in rejected] == (["price per m² outside 10,000 to 400,000"] if quarantined else [])
    assert len(saved) == (not quarantined)


def test_a_listing_read_with_and_without_a_unit_type_keeps_the_typed_row_in_either_order():
    for areas in (([row(1, unit_type=None)], [row(1)]), ([row(1)], [row(1, unit_type=None)])):
        seen, counts, saved = set(), Counter(), []
        for rows in areas:
            area_counts, area_saved, rejected = tracker.check(rows, seen, {}, typed={("nawy", "1")})
            counts, saved = counts + area_counts, saved + area_saved
            assert not rejected
        assert counts == Counter(parsed=2, duplicate=1, saved=1)
        assert [r["unit_type"] for r in saved] == ["Apartment"]


def test_a_laboratory_card_is_skipped_not_quarantined():
    counts, _, rejected = tracker.check([row(1, unit_type=sites.unit_type("Laboratory"))], set(),
                                        {("nawy", "1"): "unit page not read"})
    assert counts == Counter(parsed=1, skipped=1) and not rejected


def test_fetch_logs_the_url_the_site_answered_from(monkeypatch, tmp_path):
    def get(url, timeout):
        response = requests.Response()
        response.status_code, response._content, response.url = 200, b"<html></html>", url + "-moved"
        return response
    monkeypatch.setattr(tracker.http, "get", get)
    monkeypatch.setattr(tracker.time, "sleep", lambda seconds: None)
    tracker.fetch(SimpleNamespace(can_fetch=lambda agent, url: True), tmp_path, UNIT_URL)
    (logged,) = tracker.read_csv(tmp_path / "index.csv")
    assert (logged["url"], logged["final_url"]) == (UNIT_URL, UNIT_URL + "-moved")


def test_reconciliation_fails_loudly_on_a_mismatch():
    with pytest.raises(RuntimeError, match="do not reconcile"):
        tracker.reconcile(Counter(parsed=9, skipped=2, duplicate=1, saved=2, quarantined=3), "test")


def fake_site(monkeypatch, priced=True, has_next=True, residential=45):
    """A JSON site whose every page holds 45 rows, `residential` of them apartments in New Cairo."""
    calls = []

    def get(url, pace):
        calls.append(url)
        response = requests.Response()
        response.status_code, response._content, response.url = 200, b"page", url
        return response

    def parse(block, url):
        return [row(i, unit_type="Apartment" if i < residential else "Office", price=Decimal(1) if priced else None)
                for i in range(45)], has_next
    monkeypatch.setattr(tracker.sites, "get", get)
    monkeypatch.setitem(tracker.sites.SITES, "nawy", (lambda text, url: {"page": url}, parse))
    search = {"source": "nawy", "area_id": "new-cairo", "search": "all", "url_template": "u?page={page}", "max_pages": 17}
    return calls, search


@pytest.mark.parametrize("residential, has_next, pages", [
    (45, True, 4),   # 150 residential rows reached on page 4
    (5, True, 17),   # mostly offices: stops at max_pages
    (45, False, 1),  # the search has one page
])
def test_a_search_is_read_until_150_rows_or_max_pages(monkeypatch, tmp_path, residential, has_next, pages):
    calls, search = fake_site(monkeypatch, has_next=has_next, residential=residential)
    tracker.read_search("nawy", search, tmp_path)
    assert len(calls) == pages
    assert len(list(tmp_path.glob("*.json.gz"))) == pages == len(tracker.read_csv(tmp_path / "index.csv"))
    tracker.read_search("nawy", search, tmp_path)  # a retried task reads its pages from disk
    assert len(calls) == pages


def test_canary_fails_loudly_when_page_1_has_no_price(monkeypatch, tmp_path):
    calls, search = fake_site(monkeypatch, priced=False)
    with pytest.raises(RuntimeError, match="Canary"):
        tracker.read_search("nawy", search, tmp_path)


def test_a_finished_week_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr(tracker, "RAW", tmp_path)
    (tmp_path / "nawy" / "2026-10-04").mkdir(parents=True)
    (tmp_path / "nawy" / "2026-10-04" / "_done").write_text("")
    monkeypatch.setattr(tracker, "read_search", lambda *a: pytest.fail("a finished week was read again"))
    tracker.extract("nawy", date(2026, 10, 4))


needs_warehouse = pytest.mark.skipif(not os.environ.get("WAREHOUSE_PASSWORD"),
                                     reason="needs the warehouse: set WAREHOUSE_PASSWORD")


@needs_warehouse
def test_price_change_over_two_synthetic_weeks():
    """Three listings over two weeks: a cut, a rise and an unchanged price. Rolled back."""
    conn = tracker.connect()
    try:
        conn.execute((tracker.ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        conn.execute("INSERT INTO silver.area (area_id, name) VALUES ('test-area', 'Test area')")
        for listing_id, old, new in (("t-1", 5000000, 4500000), ("t-2", 5000000, 5250000), ("t-3", 5000000, 5000000)):
            conn.execute("INSERT INTO silver.listing (source, listing_id, area_id, unit_type, size_m2, first_seen_week,"
                         " last_seen_week) VALUES ('nawy', %s, 'test-area', 'Apartment', 100, '2099-01-04', '2099-01-11')",
                         (listing_id,))
            for week, price in (("2099-01-04", old), ("2099-01-11", new)):
                conn.execute("INSERT INTO silver.price_observation (source, listing_id, run_week, asking_price, size_m2,"
                             " fetched_at) VALUES ('nawy', %s, %s, %s, 100, now())", (listing_id, week, price))
        for week in (date(2099, 1, 4), date(2099, 1, 11)):
            tracker.build_gold(week, conn)
        assert conn.execute(
            "SELECT listing_id, old_week_key, week_key, old_price_per_m2, new_price_per_m2, change_pct, is_cut"
            " FROM gold.price_change WHERE listing_id LIKE 't-%' ORDER BY listing_id").fetchall() == [
            ("t-1", date(2099, 1, 4), date(2099, 1, 11), Decimal("50000.00"), Decimal("45000.00"), Decimal("-10.00"), True),
            ("t-2", date(2099, 1, 4), date(2099, 1, 11), Decimal("50000.00"), Decimal("52500.00"), Decimal("5.00"), False),
        ]
    finally:
        conn.rollback()
        conn.close()


@needs_warehouse
def test_a_price_quarantined_in_its_week_stays_in_silver_and_leaves_gold():
    """q-1 priced in weeks 2099-01-04 and 2099-01-11 and quarantined in the second: silver keeps both prices,
    gold keeps only the first. Rolled back."""
    conn = tracker.connect()
    try:
        conn.execute((tracker.ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        conn.execute("INSERT INTO silver.area (area_id, name) VALUES ('test-area', 'Test area')")
        conn.execute("INSERT INTO silver.listing (source, listing_id, area_id, unit_type, size_m2, first_seen_week,"
                     " last_seen_week) VALUES ('nawy', 'q-1', 'test-area', 'Apartment', 100, '2099-01-04', '2099-01-11')")
        for week in ("2099-01-04", "2099-01-11"):
            conn.execute("INSERT INTO silver.price_observation (source, listing_id, run_week, asking_price, size_m2,"
                         " fetched_at) VALUES ('nawy', 'q-1', %s, 5000000, 100, now())", (week,))
        conn.execute("INSERT INTO silver.quarantine (run_week, source, url, reason, payload) VALUES ('2099-01-11',"
                     " 'nawy', 'uq-1', %s, '{\"source_listing_id\": \"q-1\"}')", (tracker.OUTSIDE_BAND,))
        for week in (date(2099, 1, 4), date(2099, 1, 11)):
            tracker.build_gold(week, conn)
        assert conn.execute("SELECT count(*) FROM silver.price_observation WHERE listing_id = 'q-1'").fetchone()[0] == 2
        assert conn.execute("SELECT week_key FROM gold.fact_listing_price WHERE listing_id = 'q-1'").fetchall() == [
            (date(2099, 1, 4),)]
    finally:
        conn.rollback()
        conn.close()


@needs_warehouse
def test_pooled_views_leave_out_a_bayut_copy_of_a_dubizzle_ad():
    """One ad on Dubizzle and on Bayut in the same week: the fact table and the per-site view keep both,
    the pooled views count it once. Rolled back."""
    conn = tracker.connect()
    try:
        conn.execute((tracker.ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        conn.execute("INSERT INTO silver.area (area_id, name) VALUES ('test-area', 'Test area')")
        for source in ("dubizzle", "bayut"):
            conn.execute("INSERT INTO silver.listing (source, listing_id, area_id, unit_type, size_m2, first_seen_week,"
                         " last_seen_week) VALUES (%s, 'm-1', 'test-area', 'Apartment', 100, '2099-01-04', '2099-01-04')",
                         (source,))
            conn.execute("INSERT INTO silver.price_observation (source, listing_id, run_week, asking_price, size_m2,"
                         " fetched_at) VALUES (%s, 'm-1', '2099-01-04', 5000000, 100, now())", (source,))
        tracker.build_gold(date(2099, 1, 4), conn)
        area = "(SELECT area_key FROM gold.dim_area WHERE area_id = 'test-area')"
        assert conn.execute(f"SELECT count(*) FROM gold.fact_listing_price WHERE area_key = {area}").fetchone()[0] == 2
        assert conn.execute(f"SELECT count(*) FROM gold.area_site_benchmark WHERE area_key = {area}").fetchone()[0] == 2
        assert conn.execute(f"SELECT listings FROM gold.area_benchmark WHERE area_key = {area}").fetchall() == [(1,)]
        assert conn.execute(f"SELECT s.source FROM gold.pooled_listing_price JOIN gold.dim_site s USING (site_key)"
                            f" WHERE area_key = {area}").fetchall() == [("dubizzle",)]
    finally:
        conn.rollback()
        conn.close()


GOLD_FINGERPRINT = """
SELECT (SELECT count(*) FROM gold.fact_listing_price WHERE week_key = %(w)s),
       (SELECT md5(string_agg(f::text, '|' ORDER BY site_key, listing_id)) FROM gold.fact_listing_price f WHERE week_key = %(w)s),
       (SELECT count(*) FROM gold.fact_our_unit),
       (SELECT md5(string_agg(u::text, '|' ORDER BY unit_code)) FROM gold.fact_our_unit u),
       (SELECT md5(string_agg(d::text, '|' ORDER BY site_key)) FROM gold.dim_site d),
       (SELECT md5(string_agg(d::text, '|' ORDER BY area_key)) FROM gold.dim_area d),
       (SELECT md5(string_agg(d::text, '|' ORDER BY compound_key)) FROM gold.dim_compound d),
       (SELECT md5(string_agg(d::text, '|' ORDER BY type_key)) FROM gold.dim_property_type d),
       (SELECT md5(string_agg(d::text, '|' ORDER BY week_key)) FROM gold.dim_week d)
"""


@needs_warehouse
def test_rebuilding_gold_for_a_week_twice_gives_the_same_rows():
    """The latest loaded week, rebuilt twice: same counts and md5 over every fact and dimension. Rolled back."""
    conn = tracker.connect()
    try:
        conn.execute((tracker.ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        week = conn.execute("SELECT max(run_week) FROM silver.price_observation").fetchone()[0]
        if week is None:
            pytest.skip("no week loaded yet")
        tracker.build_gold(week, conn)
        first = conn.execute(GOLD_FINGERPRINT, {"w": week}).fetchone()
        tracker.build_gold(week, conn)
        assert conn.execute(GOLD_FINGERPRINT, {"w": week}).fetchone() == first
        assert first[0] > 0
    finally:
        conn.rollback()
        conn.close()


@needs_warehouse
def test_rejected_row_goes_to_quarantine_once():
    """A rejected row is kept with its reason and what was parsed; saving it again adds nothing."""
    conn = tracker.connect()
    try:
        conn.execute((tracker.ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        conn.execute("INSERT INTO silver.area (area_id, name) VALUES ('test-area', 'Test area')")
        part = {"pages": ["test.json.gz"], "stated_total": None}
        for _ in range(2):
            tracker.save(conn, date(2099, 1, 4), "nawy", "test-area", part, Counter(parsed=1, quarantined=1), [],
                         [("price missing or <= 0", row("q-1", price=None))])
        assert conn.execute("SELECT reason, payload->>'size_m2', payload ? 'asking_price' FROM silver.quarantine"
                            " WHERE url = 'uq-1'").fetchall() == [("price missing or <= 0", "100", True)]
        assert conn.execute("SELECT pages_read, pages_used FROM silver.run_log WHERE area_id = 'test-area'").fetchone() == (
            1, ["test.json.gz"])
    finally:
        conn.rollback()
        conn.close()


@needs_warehouse
def test_a_reload_that_saves_a_different_set_passes_the_saved_check():
    """Week 2099-01-04 first loaded with listings s-1 and s-2, then reloaded saving s-1 and s-3: the check
    passes (prices are append-only, s-2 stays); a key that never reached silver fails it. Rolled back."""
    conn = tracker.connect()
    try:
        conn.execute((tracker.ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        conn.execute("INSERT INTO silver.area (area_id, name) VALUES ('test-area', 'Test area')")
        week, part = date(2099, 1, 4), {"pages": ["test.json.gz"], "stated_total": None}
        for ids in (("s-1", "s-2"), ("s-1", "s-3")):
            saved = [row(i, area="test-area") for i in ids]
            tracker.save(conn, week, "nawy", "test-area", part, Counter(parsed=2, saved=2), saved, [])
            tracker.check_saved(conn, week, {("nawy", i) for i in ids})
        assert conn.execute("SELECT count(*) FROM silver.price_observation WHERE run_week = %s", (week,)).fetchone()[0] == 3
        with pytest.raises(RuntimeError, match="not in silver"):
            tracker.check_saved(conn, week, {("nawy", "s-1"), ("nawy", "never-saved")})
    finally:
        conn.rollback()
        conn.close()


def units_file(monkeypatch, tmp_path, text):
    monkeypatch.setitem(tracker.CFG, "input_dir", tmp_path)
    monkeypatch.setattr(tracker, "ROOT", tmp_path.parent)
    (tmp_path / tracker.CFG["inputs"]["units"]).write_text(text, encoding="utf-8")


HEADER = "unit_code,area_id,compound,developer,unit_type,bedrooms,size_m2,asking_price,floor\n"


def test_the_demo_units_file_passes_its_checks():
    units = tracker.read_units()
    assert len(units) == 60 and list(units[0]) == tracker.UNIT_COLUMNS  # the extra columns are not loaded


@pytest.mark.parametrize("body, message", [
    (HEADER.replace(",size_m2", "") + "U1,new-cairo,C,,Apartment,3,9000000,4\n",
     "our_units.csv is missing column(s): size_m2"),
    (HEADER + "U1,alexandria,C,,Apartment,3,100,9000000,4\n",
     "our_units.csv line 2 (U1): area alexandria is not an id under areas in config/client.yaml"),
    (HEADER + "U1,new-cairo,C,,Igloo,3,100,9000000,4\n",
     "our_units.csv line 2 (U1): unit type Igloo is not in rules.unit_types in config/client.yaml"),
    (HEADER + "U1,new-cairo,C,,Apartment,3,100,9000000,4\nU2,new-cairo,C,,Apartment,3,0,9000000,4\n",
     "our_units.csv line 3 (U2): size_m2 and asking_price must be numbers above 0"),
    (HEADER + "U1,new-cairo,C,,Apartment,3,100,-5,4\n",
     "our_units.csv line 2 (U1): size_m2 and asking_price must be numbers above 0"),
    (HEADER, "our_units.csv has no units"),
])
def test_a_bad_units_file_stops_with_one_line(monkeypatch, tmp_path, body, message):
    units_file(monkeypatch, tmp_path, body)
    with pytest.raises(SystemExit) as stop:
        tracker.read_units()
    assert str(stop.value).endswith(message) and "\n" not in str(stop.value)


def test_a_missing_units_file_names_its_config_key(monkeypatch, tmp_path):
    monkeypatch.setitem(tracker.CFG, "input_dir", tmp_path)
    monkeypatch.setattr(tracker, "ROOT", tmp_path.parent)
    with pytest.raises(SystemExit, match=r"missing input file .*our_units.csv \(inputs.units in config/client.yaml\)"):
        tracker.read_units()


def test_load_silver_checks_the_units_before_touching_the_warehouse(monkeypatch, tmp_path):
    units_file(monkeypatch, tmp_path, HEADER + "U1,alexandria,C,,Apartment,3,100,9000000,4\n")
    monkeypatch.setattr(tracker, "connect", lambda: pytest.fail("the warehouse was touched"))
    with pytest.raises(SystemExit, match="area alexandria"):
        tracker.load_silver(date(2026, 10, 4))


def test_an_empty_week_fails_loudly(monkeypatch, tmp_path):
    """A week whose automated sites have no finished folder, and a week whose folders hold no page."""
    class Warehouse:
        """Stands in for the warehouse: takes every statement, holds nothing."""
        info = SimpleNamespace(dbname="prices")
        __enter__, __exit__ = (lambda self: self), (lambda self, *a: None)
        execute = lambda self, *a: self  # noqa: E731
        cursor = lambda self: self  # noqa: E731
        executemany = lambda self, *a: None  # noqa: E731
        fetchone = lambda self: (0,)  # noqa: E731
    monkeypatch.setattr(tracker, "connect", Warehouse)
    monkeypatch.setattr(tracker, "RAW", tmp_path)
    with pytest.raises(RuntimeError, match="has no _done: its extract did not finish"):
        tracker.load_silver(date(2026, 10, 4))
    for source in tracker.AUTOMATED:
        (tmp_path / source / "2026-10-04").mkdir(parents=True)
        (tmp_path / source / "2026-10-04" / "_done").write_text("")
    with pytest.raises(RuntimeError, match="No asking price saved for 2026-10-04"):
        tracker.load_silver(date(2026, 10, 4))


def test_no_password_stops_with_one_line(monkeypatch):
    monkeypatch.delenv("WAREHOUSE_PASSWORD", raising=False)
    with pytest.raises(SystemExit, match=r"^WAREHOUSE_PASSWORD is not set \(copy .env.example to .env; outside Docker, export it\)$"):
        tracker.connect()
