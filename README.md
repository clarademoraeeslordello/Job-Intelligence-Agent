# Job Intelligence Agent

Agente de IA que busca vagas automaticamente, entende o perfil profissional do usuário e recomenda apenas oportunidades compatíveis — funcionando como um recrutador pessoal baseado em contexto (currículo, experiência, preferências), não apenas um agregador de vagas.

Visão completa do produto e arquitetura em [`docs/`](docs/):

- [`architecture.md`](architecture.md) — arquitetura e stack
- [`product-requirements.md`](product-requirements.md) — PRD
- [`database-design.md`](database-design.md) — modelo de dados
- [`crawler-strategy.md`](crawler-strategy.md) — estratégia de coleta de vagas
- [`ai-engine.md`](ai-engine.md) — motor de IA (Claude API)
- [`development-guidelines.md`](development-guidelines.md) — regras de código
- [`roadmap.md`](roadmap.md) — roadmap de produto
- [`docs/development-plan.md`](docs/development-plan.md) — análise de arquitetura + plano de execução incremental
- [`docs/po-backlog.md`](docs/po-backlog.md) — passo a passo para criar credenciais e colocar o agente pra rodar de verdade

**Status atual:** Fases 1–6 do `docs/development-plan.md` implementadas e testadas (54/54 testes, sem chamadas reais de API). Busca abrangente via `ArbeitnowCrawler`/`RemoteOKCrawler` (sem lista de empresas) + scheduler via GitHub Actions (`.github/workflows/daily-run.yml`, diário) + backoffice web de acesso (`app/web/`) já implementados. Falta só você criar as credenciais e escolher onde hospedar o backoffice — passo a passo completo em [`docs/po-backlog.md`](docs/po-backlog.md).

---

## Stack

- Python 3.13
- SQLAlchemy 2.0 + Alembic (migrations) — SQLite no MVP, PostgreSQL futuro
- pydantic-settings (configuração tipada via `.env`)
- pytest + black

Gerenciamento de dependências e ambiente via [`uv`](https://docs.astral.sh/uv/).

---

## Setup local

1. Instale o [`uv`](https://docs.astral.sh/uv/getting-started/installation/) (gerencia Python e dependências).
2. Instale as dependências do projeto:

   ```bash
   uv sync
   ```

3. Copie o arquivo de ambiente e preencha os valores necessários:

   ```bash
   cp .env.example .env
   ```

   `DATABASE_URL` é obrigatória. `CLAUDE_API_KEY`, `TELEGRAM_TOKEN` e `GREENHOUSE_BOARD_TOKENS` são opcionais — sem elas, `app/main.py` roda em modo degradado (loga e pula a etapa que depende da credencial faltante, sem quebrar). Ver [`docs/po-backlog.md`](docs/po-backlog.md).

4. Aplique as migrations (cria `data/database.sqlite`):

   ```bash
   uv run alembic upgrade head
   ```

5. Rode os testes:

   ```bash
   uv run pytest
   ```

6. Rode um ciclo completo (coleta → análise → notificação), com degradação graciosa se faltar credencial:

   ```bash
   uv run python -m app.main
   ```

7. Rode o backoffice web (login + gestão de acesso) localmente:

   ```bash
   uv run uvicorn app.web.app:app --reload --port 8010
   ```

   Acesse `http://localhost:8010/login`. Para o primeiro acesso, defina `is_admin=True` e uma senha manualmente no banco (não há UI de "primeiro admin" ainda — ver `docs/po-backlog.md`).

---

## Estrutura do projeto

```
app/
  main.py                    # entrypoint manual: coleta -> analise -> notificacao
  config.py                  # configuracao tipada (pydantic-settings)
  logging_config.py
  database/
    database.py               # engine/session SQLAlchemy
    models.py                  # User, Profile, Resume, Job, JobAnalysis, Application, Notification
  crawler/
    base.py                    # BaseCrawler + JobDTO (contrato)
    arbeitnow.py                 # ArbeitnowCrawler (busca abrangente, sem config)
    greenhouse.py                 # GreenhouseCrawler (API JSON, sem Playwright)
    runner.py                      # CrawlerRunner (isola falha por fonte)
  seed.py                     # cadastra/atualiza usuario a partir de env vars (Secrets)
  ai/
    context_builder.py          # User Context Engine
    prompts.py
    analyzer.py                  # chamada a Claude API (client injetavel)
    scorer.py                     # validacao/normalizacao da resposta da IA
  notifications/
    telegram.py                  # TelegramNotifier (httpx direto)
  services/
    jobs_service.py               # dedup + persistencia de vagas
    analysis_service.py            # persiste JobAnalysis (nunca sobrescreve)
    notification_service.py         # dedup de notificacao + threshold por usuario
  web/
    app.py                        # FastAPI: login + backoffice de acesso
    security.py                    # hash/verify de senha (bcrypt), cookie de sessao assinado
    deps.py                        # dependencias de auth (require_login, require_admin)
    templates/                     # Jinja2, responsivo (mobile + desktop)
    static/style.css
data/
  database.sqlite               # banco local (git-ignored)
  resumes/                        # curriculos dos usuarios (git-ignored)
migrations/                      # Alembic
tests/                            # 54 testes, todos com mocks (sem chamadas reais de API)
```

---

## Convenções

Ver [`development-guidelines.md`](development-guidelines.md) para regras de código, testes e segurança. Resumo: nunca commitar segredos ou dados de `data/`, sempre type hints, sempre teste cobrindo caminho feliz + erro antes de considerar uma funcionalidade pronta.
