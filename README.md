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

**Status atual:** Sprint 1 (Fundação) em andamento — estrutura de projeto, banco SQLite e modelos iniciais (`User`, `Profile`, `Resume`).

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

   Na Sprint 1, apenas `DATABASE_URL` é usada — `CLAUDE_API_KEY` e `TELEGRAM_TOKEN` só entram nas Fases 4 e 5.

4. Aplique as migrations (cria `data/database.sqlite`):

   ```bash
   uv run alembic upgrade head
   ```

5. Rode os testes:

   ```bash
   uv run pytest
   ```

---

## Estrutura do projeto

```
app/
  config.py            # configuracao tipada (pydantic-settings)
  database/
    database.py        # engine/session SQLAlchemy
    models.py           # User, Profile, Resume (mais entidades nas proximas fases)
data/
  database.sqlite       # banco local (git-ignored)
  resumes/               # curriculos dos usuarios (git-ignored)
migrations/              # Alembic
tests/
  test_models.py
```

A estrutura completa planejada (crawlers, IA, notificações) está descrita em [`architecture.md`](architecture.md) §5 e será adicionada incrementalmente conforme [`docs/development-plan.md`](docs/development-plan.md).

---

## Convenções

Ver [`development-guidelines.md`](development-guidelines.md) para regras de código, testes e segurança. Resumo: nunca commitar segredos ou dados de `data/`, sempre type hints, sempre teste cobrindo caminho feliz + erro antes de considerar uma funcionalidade pronta.
