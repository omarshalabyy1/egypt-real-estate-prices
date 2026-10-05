"""Checks for browser_sites.py: run with `pytest`, no network needed. Each fixture is page 1 of a
search page saved by fetch_bayut_aqarmap.py on 2026-10-05, cut down to what the parser reads: the
seller, agent, agency, user, phone, WhatsApp, title and description fields were left out so no contact
data is kept in the repo. The parser gives the same rows on the cut page as on the full saved one.
Bayut's New Cairo address fell back to its Cairo page, so that page holds listings from all of Cairo."""

from decimal import Decimal
from pathlib import Path

import pytest

import browser_sites

PAGES = Path(__file__).parent / "pages"
URLS = {"bayut": "https://www.bayut.eg/en/cairo/properties-for-sale/",
        "aqarmap": "https://aqarmap.com.eg/en/for-sale/property-type/cairo/new-cairo/"}


def page(source):
    return (PAGES / f"{source}-new-cairo-page-1.html").read_text(encoding="utf-8")


def parse(source, html=None):
    return browser_sites.BROWSER_SITES[source](html or page(source), URLS[source])


def test_bayut_page():
    rows, has_next = parse("bayut")
    assert len(rows) == 24
    assert has_next
    assert sum(r["asking_price"] for r in rows) == Decimal("249380171")
    # The Cairo page: each row's area is its own city, None when that city is not one of ours.
    assert [r["area_id"] for r in rows].count(None) == 6
    assert [r["area_id"] for r in rows].count("new-cairo") == 10
    assert rows[0] == {
        "source": "bayut",
        "source_listing_id": "504204879",
        "url": "https://www.bayut.eg/en/property/details-504204879.html",
        "area_id": None,  # Shorouk City
        "compound": "El Shorouk 2000",
        "developer": None,
        "unit_type": "Villa",
        "bedrooms": 3,
        "bathrooms": 4,
        "size_m2": Decimal("386"),
        "asking_price": Decimal("14000000"),
        "listed_on": None,
    }


def test_aqarmap_page():
    rows, has_next = parse("aqarmap")
    assert len(rows) == 22  # 22 cards; the shorter footer copy of a listing is skipped
    assert has_next
    assert sum(r["asking_price"] for r in rows) == Decimal("276600750")
    assert rows[0] == {
        "source": "aqarmap",
        "source_listing_id": "7317020",
        "url": "https://aqarmap.com.eg/en/listing/7317020-for-sale-cairo-new-cairo-compounds-fifth-square",
        "area_id": "new-cairo",
        "compound": "Fifth Square Compound",  # Aqarmap writes "Fifth Square Compound - AlMarasem"
        "developer": "AlMarasem",
        "unit_type": None,  # a /for-sale/property-type/ page gives no unit type
        "bedrooms": 3,
        "bathrooms": 3,
        "size_m2": Decimal("207"),
        "asking_price": Decimal("15700000"),
        "listed_on": None,
    }


def test_aqarmap_unit_type_comes_from_the_page_asked_for():
    for asked, expected in (("apartment", "Apartment"), ("twinhouse", "Twin House"), ("property-type", None)):
        rows, _ = browser_sites.parse_aqarmap(page("aqarmap"), f"https://aqarmap.com.eg/en/for-sale/{asked}/cairo/new-cairo/")
        assert {r["unit_type"] for r in rows} == {expected}


@pytest.mark.parametrize("source", browser_sites.BROWSER_SITES)
def test_last_page_has_no_next(source):
    html = page(source)
    head, rest = html.split('<link rel="next"', 1)
    assert not parse(source, head + rest.split(">", 1)[1])[1]


@pytest.mark.parametrize("source", browser_sites.BROWSER_SITES)
def test_parsing_twice_gives_the_same_rows(source):
    assert repr(parse(source)) == repr(parse(source))


@pytest.mark.parametrize("source", browser_sites.BROWSER_SITES)
@pytest.mark.parametrize("html", ["<html><body></body></html>", "<html><body><p>Access denied</p></body></html>"])
def test_page_without_listings_fails_loudly(source, html):
    with pytest.raises(RuntimeError):
        browser_sites.BROWSER_SITES[source](html, URLS[source])


def test_bayut_page_without_item_list_fails_loudly():
    # The national page saved on 2026-10-05 had JSON-LD without an ItemList.
    with pytest.raises(RuntimeError):
        browser_sites.parse_bayut('<script type="application/ld+json">{"@graph": [{"name": "Egypt"}]}</script>', "u")
    cards_removed = page("bayut").split("<ul>")[0]
    with pytest.raises(RuntimeError):
        browser_sites.parse_bayut(cards_removed, "u")


def test_aqarmap_matches_the_deepest_path_first():
    """Aqarmap files Mostakbal City under New Cairo: its listings must not become New Cairo rows."""
    paths = list(browser_sites.AQARMAP_AREAS)
    assert paths.index("cairo/new-cairo/lmstqbl-syty") < paths.index("cairo/new-cairo")
    slug = "cairo/new-cairo/lmstqbl-syty/compounds/some-compound"
    assert next(a for p, a in browser_sites.AQARMAP_AREAS.items() if slug == p or slug.startswith(p + "/")) == "mostakbal-city"
