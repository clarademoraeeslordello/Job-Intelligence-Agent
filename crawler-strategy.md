# Crawler Strategy

**Produto:** Job Intelligence Agent

---

## 1. Objetivo

Definir como as vagas são coletadas, garantindo que:

- Novos conectores (fontes de vagas) possam ser adicionados sem alterar o núcleo do sistema.
- Não haja duplicação de vagas.
- O sistema seja resiliente a falhas (site fora do ar, mudança de layout, etc.).
- As boas práticas de scraping sejam respeitadas (sem sobrecarregar as fontes).

---

## 2. Fontes

### Prioridade alta
1. **Greenhouse**
2. **Lever**

### Prioridade média
3. **Ashby**
4. **Workday**

Critério de priorização: volume de empresas relevantes usando a plataforma + facilidade de extração (Greenhouse e Lever expõem estrutura mais previsível).

---

## 3. Regras Gerais

Todo crawler deve:

- Herdar de `BaseCrawler`.
- Retornar sempre um `JobDTO` (objeto padronizado), nunca um dicionário solto ou HTML cru.
- Ter tratamento de erro (timeout, página não encontrada, layout alterado) sem derrubar o processo inteiro.
- Salvar logs de execução (quantas vagas encontradas, quantas novas, quantas ignoradas, erros).
- Não duplicar vagas — usar `(source, external_id)` como chave de deduplicação antes de persistir.
- Respeitar rate limiting: intervalo mínimo entre requisições e uso responsável do Playwright (não abrir dezenas de páginas em paralelo contra o mesmo domínio).

---

## 4. Interface Base

```python
class BaseCrawler:
    """
    Interface que todo crawler de vagas deve implementar.
    """

    source_name: str  # ex: "greenhouse"

    def search_jobs(self) -> list[dict]:
        """
        Executa a busca de vagas na fonte.
        Retorna dados brutos (pré-normalização).
        """
        raise NotImplementedError

    def parse_job(self, raw_job: dict) -> "JobDTO":
        """
        Transforma um item bruto em um JobDTO padronizado.
        """
        raise NotImplementedError
```

### JobDTO (contrato de saída)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class JobDTO:
    title: str
    company: str
    location: Optional[str]
    country: Optional[str]
    remote: bool
    salary: Optional[str]
    description: str
    requirements: Optional[str]
    url: str
    source: str
    external_id: str
```

Todo crawler específico (`GreenhouseCrawler`, `LeverCrawler`, etc.) implementa `search_jobs` e `parse_job`, mas sempre entrega um `JobDTO` ao restante do sistema. O `Job Normalizer` (ver `architecture.md`) recebe esses DTOs e persiste no banco.

---

## 5. Exemplo de Implementação

```python
class GreenhouseCrawler(BaseCrawler):
    source_name = "greenhouse"

    def search_jobs(self) -> list[dict]:
        # usa Playwright para navegar e coletar vagas brutas
        ...

    def parse_job(self, raw_job: dict) -> JobDTO:
        return JobDTO(
            title=raw_job["title"],
            company=raw_job["company"],
            location=raw_job.get("location"),
            country=raw_job.get("country"),
            remote=raw_job.get("remote", False),
            salary=raw_job.get("salary"),
            description=raw_job["description"],
            requirements=raw_job.get("requirements"),
            url=raw_job["url"],
            source=self.source_name,
            external_id=raw_job["id"],
        )
```

---

## 6. Fluxo de Execução

```
Scheduler
  |
  v
CrawlerRunner (orquestra todos os crawlers ativos)
  |
  +--> GreenhouseCrawler.search_jobs()
  +--> LeverCrawler.search_jobs()
  |
  v
parse_job() para cada item bruto → JobDTO
  |
  v
Job Normalizer (dedup + validação)
  |
  v
SQLite (tabela jobs)
```

---

## 7. Tratamento de Erros

- Cada crawler deve capturar exceções individualmente — falha em uma fonte não pode impedir a execução das demais.
- Erros devem ser logados com contexto suficiente (fonte, timestamp, mensagem) para debug posterior.
- Se um crawler falhar 3 execuções seguidas, deve gerar um alerta (ex: notificação de sistema, separada das notificações de vaga).

---

## 8. Extensibilidade

Para adicionar uma nova fonte:

1. Criar `app/crawler/<nova_fonte>.py`.
2. Implementar `BaseCrawler`.
3. Registrar o crawler no `CrawlerRunner` (arquivo de configuração ou registro dinâmico).
4. Nenhuma alteração deve ser necessária em `Job Normalizer`, banco de dados ou IA — o contrato `JobDTO` já garante compatibilidade.
