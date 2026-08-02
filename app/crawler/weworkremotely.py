import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.crawler.base import BaseCrawler, JobDTO

FEED_URL_TEMPLATE = "https://weworkremotely.com/categories/{category}.rss"

DEFAULT_CATEGORIES = ("remote-product-jobs", "remote-management-and-finance-jobs")
# Categorias do WWR que concentram produto, projeto e analise. Nao existe
# "remote-data-jobs" (o site responde HTML de erro, nao RSS) - analista de dados
# aparece diluido nessas duas.


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def _split_company_and_title(raw_title: str) -> tuple[str, str]:
    """WWR publica o titulo como "Empresa: Cargo | Regiao".

    Sem os dois pontos nao da para saber a empresa - devolve vazio em vez de
    inventar, e quem chama decide (aqui, o item e descartado por parse_job).
    """
    company, separator, title = raw_title.partition(":")
    if not separator:
        return "", raw_title.strip()
    return company.strip(), title.strip()


class WeWorkRemotelyCrawler(BaseCrawler):
    """Crawler via feeds RSS publicos do WeWorkRemotely, por categoria.

    Terceira fonte, adicionada em 02/08/2026 depois de medir que as duas
    primeiras nao entregavam vaga remota de produto/projeto/dados: Arbeitnow e
    ~91% presencial e alemao, e RemoteOK traz ~25 vagas/dia so de engenharia.
    O WWR e 100% remoto e tem categoria propria de produto.

    Nao substitui LinkedIn/Indeed/Glassdoor - esses nao tem API publica de busca
    (a do Indeed foi descontinuada, a do Glassdoor fechada, a do LinkedIn e
    parceiro-only) e proibem scraping. Cobertura equivalente por via legitima
    depende de agregadores com chave de API (Adzuna, Jooble).
    """

    source_name = "weworkremotely"

    def __init__(
        self,
        lookback_hours: int = 48,
        categories: tuple[str, ...] = DEFAULT_CATEGORIES,
        client: httpx.Client | None = None,
    ) -> None:
        self.lookback_hours = lookback_hours
        self.categories = categories
        self._client = client or httpx.Client(
            timeout=20.0,
            headers={"User-Agent": "job-intelligence-agent/0.1"},
            follow_redirects=True,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _fetch_category(self, category: str) -> str:
        response = self._client.get(FEED_URL_TEMPLATE.format(category=category))
        response.raise_for_status()
        return response.text

    def search_jobs(self) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)

        items: list[dict] = []
        for category in self.categories:
            try:
                feed = self._fetch_category(category)
                root = ET.fromstring(feed)
            except (httpx.HTTPError, ET.ParseError):
                # Uma categoria fora do ar (ou slug invalido, que devolve HTML)
                # nao pode derrubar a coleta das outras.
                continue

            for item in root.findall(".//item"):
                raw = {child.tag: (child.text or "") for child in item}
                if _parse_published_at(raw.get("pubDate")) < cutoff:
                    continue
                items.append(raw)

        return items

    def parse_job(self, raw_job: dict) -> JobDTO:
        company, title = _split_company_and_title(raw_job.get("title", ""))
        if not company or not title:
            raise ValueError("titulo do WWR fora do formato 'Empresa: Cargo'")

        link = raw_job.get("link") or ""
        if not link:
            raise ValueError("item do WWR sem link")

        return JobDTO(
            title=title,
            company=company,
            location=raw_job.get("region") or "Remote",
            country=raw_job.get("country") or None,
            remote=True,
            # O WWR e um board exclusivamente remoto - nao ha vaga presencial no
            # feed, entao a flag e verdadeira por construcao da fonte.
            salary=None,
            description=_strip_html(raw_job.get("description", "")),
            requirements=None,
            url=link,
            source=self.source_name,
            external_id=raw_job.get("guid") or link,
        )


def _parse_published_at(pub_date: str | None) -> datetime:
    """Data do item; itens sem data legivel entram como agora, para nao sumirem
    silenciosamente da janela de coleta."""
    if not pub_date:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(pub_date)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
