"""Checks for the parts of sites.py that break when a site changes its pages: run with `pytest`, no
network needed. Each fixture is page 1 of New Cairo as read on 2026-10-05, cut down to the JSON keys
the parser reads: the agent, broker, seller, contact, title and description fields were left out so
no contact data is kept in the repo. The parser gives the same rows on the cut page as on the full one."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import sites

PAGES = Path(__file__).parent / "pages"


def parse(source, page=1):
    text = (PAGES / f"{source}-new-cairo-page-1.html").read_text(encoding="utf-8")
    return sites.SITES[source][1](text, sites.URLS[source, "new-cairo"].format(page=page))


def test_propertyfinder_page():
    rows, has_next = parse("propertyfinder")
    assert len(rows) == 20  # 30 cards: 20 listings, 5 projects and 5 project unit ranges skipped
    assert has_next
    assert sum(r["asking_price"] for r in rows) == Decimal("398864500")
    assert rows[0] == {
        "source": "propertyfinder",
        "source_listing_id": "114357350",
        "url": "https://www.propertyfinder.eg/en/plp/buy/apartment-for-sale-cairo-new-cairo-city-el-katameya-el-katameya-compounds-west-golf-114357350.html",
        "area_id": "new-cairo",
        "compound": "West Golf",
        "developer": None,
        "unit_type": "Apartment",
        "bedrooms": 4,
        "bathrooms": 3,
        "size_m2": Decimal("325"),
        "asking_price": Decimal("10400000"),
        "listed_on": date(2026, 10, 3),
    }


def test_dubizzle_page():
    rows, has_next = parse("dubizzle")
    assert len(rows) == 45
    assert has_next
    assert sum(r["asking_price"] for r in rows) == Decimal("431349359")
    assert rows[0] == {
        "source": "dubizzle",
        "source_listing_id": "504204845",
        "url": "https://www.dubizzle.com.eg/en/ad/apartment-for-sale-in-taj-city-on-suez-road-minutes-to-mivida-hydepark-and-sarai-ID504204845.html",
        "area_id": "new-cairo",
        "compound": "Taj City Compound",
        "developer": None,
        "unit_type": "Apartment",
        "bedrooms": 1,
        "bathrooms": 1,
        "size_m2": Decimal("53"),
        "asking_price": Decimal("2732400"),
        "listed_on": date(2026, 10, 4),
    }


def test_dubizzle_last_page_has_no_next():
    # 34,876 ads at 45 a page: page 776 is the last. The site's own nbPages (2,139) is not used.
    assert parse("dubizzle", page=775)[1]
    assert not parse("dubizzle", page=776)[1]


def test_nawy_page():
    rows, has_next = parse("nawy")
    assert len(rows) == 12
    assert has_next
    assert sum(r["asking_price"] for r in rows) == Decimal("349886000")
    assert [r["area_id"] for r in rows].count("mostakbal-city") == 1  # Nawy files Mostakbal City under New Cairo
    assert rows[0] == {
        "source": "nawy",
        "source_listing_id": "55420",
        "url": "https://www.nawy.com/compound/23-villette/property/55420-apartment-for-sale-in-villette-with-2-bedrooms-in-golden-square-by-sodic",
        "area_id": "new-cairo",
        "compound": "Villette",
        "developer": "SODIC",
        "unit_type": "Apartment",
        "bedrooms": 2,
        "bathrooms": 3,
        "size_m2": Decimal("139"),
        "asking_price": Decimal("15600000"),
        "listed_on": None,
    }


@pytest.mark.parametrize("source", sites.SITES)
def test_parsing_twice_gives_the_same_rows(source):
    assert repr(parse(source)) == repr(parse(source))


@pytest.mark.parametrize("source", sites.SITES)
@pytest.mark.parametrize("html", ["<html><body></body></html>", "<html><body><p>Access denied</p></body></html>"])
def test_page_without_its_json_fails_loudly(source, html):
    with pytest.raises(RuntimeError):
        sites.SITES[source][1](html, sites.URLS[source, "new-cairo"].format(page=1))


def test_empty_result_list_fails_loudly():
    empty = '<script id="__NEXT_DATA__" type="application/json">{}</script>'
    with pytest.raises(RuntimeError):
        sites.parse_propertyfinder(empty.replace("{}", '{"props": {"pageProps": {"searchResult": {"listings": [], "meta": {}}}}}'), "u")
    with pytest.raises(RuntimeError):
        sites.parse_nawy(empty.replace("{}", '{"props": {"pageProps": {"loadedSearchResultsSSR": {"results": []}}}}'), "u")
    with pytest.raises(RuntimeError):
        sites.parse_dubizzle('<script>window.state = {"algolia": {"content": {"hits": []}}};</script>', "u")


@pytest.mark.parametrize("label, expected", [
    ("Apartment", "Apartment"), ("Villa", "Villa"), ("Townhouse", "Town House"), ("Town House", "Town House"),
    ("Twinhouse", "Twin House"), ("Twin House", "Twin House"), ("Duplex", "Duplex"), ("Penthouse", "Penthouse"),
    ("Chalet", "Chalet"), ("Studio", "Studio"), ("Hotel Apartment", "Hotel Apartment"), ("Office", "Office"),
    ("Administrative", "Administrative"), (None, None),
])
def test_unit_type(label, expected):
    assert sites.unit_type(label) == expected


def test_propertyfinder_hidden_price_is_none():
    listing = ('{"listing_type": "property", "property": {"id": "1", "property_type": "Villa", "listed_date": null,'
               ' "price": {"value": 9000000, "currency": "EGP", "is_hidden": true}, "size": {"value": 300, "unit": "sqm"}}}')
    page = ('<script id="__NEXT_DATA__" type="application/json">{"props": {"pageProps": {"searchResult":'
            ' {"meta": {"page": 1, "page_count": 1}, "listings": [' + listing + ']}}}}</script>')
    (row,), has_next = sites.parse_propertyfinder(page, "u")
    assert row["asking_price"] is None and row["size_m2"] == Decimal("300") and not has_next


def test_get_retries_429_and_5xx_then_fails_loudly(monkeypatch):
    import requests

    def answers(*codes):
        calls = []

        def fake_get(url, timeout):
            response = requests.Response()
            response.status_code, response._content, response.url = codes[len(calls)], b"ok", url
            calls.append(url)
            return response
        monkeypatch.setattr(sites.http, "get", fake_get)
        return calls

    monkeypatch.setattr(sites.time, "sleep", lambda seconds: None)
    calls = answers(503, 429, 200)
    assert sites.get("nawy", "new-cairo", 1) == "ok" and len(calls) == 3
    calls = answers(503, 503, 503)
    with pytest.raises(requests.HTTPError):
        sites.get("nawy", "new-cairo", 1)
    assert len(calls) == 3
    calls = answers(404)
    with pytest.raises(requests.HTTPError):
        sites.get("nawy", "new-cairo", 1)
    assert len(calls) == 1  # a 404 is not tried again


def test_zero_price_and_word_rooms_are_none():
    assert sites.decimal(0) is None and sites.decimal("") is None and sites.decimal("abc") is None
    assert sites.integer("studio") is None and sites.integer("3") == 3 and sites.integer(0) == 0
