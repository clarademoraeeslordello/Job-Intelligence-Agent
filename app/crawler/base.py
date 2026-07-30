from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class JobDTO:
    """Contrato de saida de qualquer crawler (ver docs/crawler-strategy.md)."""

    title: str
    company: str
    location: str | None
    country: str | None
    remote: bool
    salary: str | None
    description: str
    requirements: str | None
    url: str
    source: str
    external_id: str


class BaseCrawler(ABC):
    """Interface que todo crawler de vagas deve implementar."""

    source_name: str

    @abstractmethod
    def search_jobs(self) -> list[dict]:
        """Executa a busca de vagas na fonte. Retorna dados brutos (pre-normalizacao)."""
        raise NotImplementedError

    @abstractmethod
    def parse_job(self, raw_job: dict) -> JobDTO:
        """Transforma um item bruto em um JobDTO padronizado."""
        raise NotImplementedError

    def collect(self) -> list[JobDTO]:
        """Executa search_jobs + parse_job para cada item, isolando erros de parsing individuais."""
        jobs: list[JobDTO] = []
        for raw_job in self.search_jobs():
            try:
                jobs.append(self.parse_job(raw_job))
            except (KeyError, TypeError, ValueError):
                continue
        return jobs
