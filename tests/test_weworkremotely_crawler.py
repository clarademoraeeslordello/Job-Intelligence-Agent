from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
import respx

from app.crawler.weworkremotely import FEED_URL_TEMPLATE, WeWorkRemotelyCrawler

NOW = datetime.now(timezone.utc)
CATEGORIES = ("remote-product-jobs",)


def _feed(*items: str) -> str:
    return f"<rss><channel>{''.join(items)}</channel></rss>"


def _item(title="EBANX: Product Manager | South Cone", hours_ago=2.0, **fields) -> str:
    data = {
        "title": title,
        "link": "https://weworkremotely.com/remote-jobs/ebanx-product-manager",
        "guid": "wwr-1",
        "region": "Anywhere in the World",
        "country": "Brazil",
        "description": "<p>Lead the <b>product</b> roadmap</p>",
        "pubDate": format_datetime(NOW - timedelta(hours=hours_ago)),
    }
    data.update(fields)
    return "<item>" + "".join(f"<{k}>{v}</{k}>" for k, v in data.items()) + "</item>"


def _mock(category: str, body: str, status: int = 200) -> None:
    respx.get(FEED_URL_TEMPLATE.format(category=category)).mock(
        return_value=httpx.Response(status, text=body)
    )


@respx.mock
def test_search_jobs_filters_by_lookback_window():
    _mock("remote-product-jobs", _feed(_item(hours_ago=2), _item(hours_ago=100, guid="wwr-2")))
    crawler = WeWorkRemotelyCrawler(lookback_hours=48, categories=CATEGORIES)

    jobs = crawler.search_jobs()

    assert [j["guid"] for j in jobs] == ["wwr-1"]


@respx.mock
def test_search_jobs_reads_every_configured_category():
    _mock("remote-product-jobs", _feed(_item(guid="a")))
    _mock("remote-management-and-finance-jobs", _feed(_item(guid="b")))
    crawler = WeWorkRemotelyCrawler(
        lookback_hours=48,
        categories=("remote-product-jobs", "remote-management-and-finance-jobs"),
    )

    jobs = crawler.search_jobs()

    assert sorted(j["guid"] for j in jobs) == ["a", "b"]


@respx.mock
def test_a_broken_category_does_not_kill_the_others():
    """Slug invalido devolve HTML, nao RSS - nao pode derrubar a coleta inteira."""
    _mock("remote-product-jobs", "<html>404</html>")
    _mock("remote-management-and-finance-jobs", _feed(_item(guid="b")))
    crawler = WeWorkRemotelyCrawler(
        lookback_hours=48,
        categories=("remote-product-jobs", "remote-management-and-finance-jobs"),
    )

    jobs = crawler.search_jobs()

    assert [j["guid"] for j in jobs] == ["b"]


def test_parse_job_splits_company_from_title():
    crawler = WeWorkRemotelyCrawler()
    raw = {
        "title": "EBANX: Product Manager | South Cone",
        "link": "https://weworkremotely.com/remote-jobs/x",
        "guid": "wwr-1",
        "region": "Anywhere in the World",
        "country": "Brazil",
        "description": "<p>Lead the <b>product</b> roadmap</p>",
    }

    dto = crawler.parse_job(raw)

    assert dto.company == "EBANX"
    assert dto.title == "Product Manager | South Cone"
    assert dto.remote is True
    assert dto.description == "Lead the product roadmap"
    assert dto.location == "Anywhere in the World"
    assert dto.source == "weworkremotely"
    assert dto.external_id == "wwr-1"


def test_parse_job_rejects_title_without_company_separator():
    """collect() isola o ValueError e pula o item, em vez de inventar empresa."""
    crawler = WeWorkRemotelyCrawler()

    with pytest.raises(ValueError):
        crawler.parse_job({"title": "Product Manager", "link": "https://x.com/1"})


def test_parse_job_rejects_item_without_link():
    crawler = WeWorkRemotelyCrawler()

    with pytest.raises(ValueError):
        crawler.parse_job({"title": "EBANX: Product Manager", "link": ""})


@respx.mock
def test_collect_skips_malformed_items_and_keeps_the_rest():
    _mock(
        "remote-product-jobs",
        _feed(_item(guid="ok"), _item(title="Sem separador de empresa", guid="bad")),
    )
    crawler = WeWorkRemotelyCrawler(lookback_hours=48, categories=CATEGORIES)

    jobs = crawler.collect()

    assert [j.external_id for j in jobs] == ["ok"]


def test_item_without_pubdate_is_kept():
    """Falta de data nao pode fazer a vaga sumir silenciosamente da janela."""
    with respx.mock:
        _mock("remote-product-jobs", _feed(_item(pubDate="")))
        crawler = WeWorkRemotelyCrawler(lookback_hours=48, categories=CATEGORIES)

        assert len(crawler.search_jobs()) == 1
