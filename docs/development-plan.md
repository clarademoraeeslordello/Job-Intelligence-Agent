# Job Intelligence Agent — Plano de Desenvolvimento

**Status:** Aguardando aprovação — nenhuma implementação foi iniciada.
**Autor:** Claude Code (análise de arquitetura + planejamento)
**Baseado em:** `architecture.md`, `product-requirements.md`, `database-design.md`, `crawler-strategy.md`, `ai-engine.md`, `api-design.md`, `development-guidelines.md`, `roadmap.md`

---

## 1. Análise da Arquitetura Atual

O projeto está em estágio **100% de documentação** — não há nenhum código, `requirements.txt`, `.env`, `.gitignore` ou `README.md` no repositório ainda. A documentação existente, no entanto, é incomum pelo nível de maturidade: já define contratos (`JobDTO`, `BaseCrawler`), regras de negócio explícitas ("Nunca"), e um conceito de produto claro (**User Context Engine**) antes de qualquer linha de código. Isso é uma base sólida para começar.

### 1.1 Pontos Fortes

- **Diferencial de produto bem definido**: o `User Context Engine` (currículo + perfil + preferências) como camada explícita, não implícita dentro do `analyzer.py`, é a decisão arquitetural mais importante do projeto — evita que a lógica de "entender o usuário" fique acoplada à lógica de "chamar a IA".
- **Contrato de crawler já pensado para extensibilidade**: `BaseCrawler` + `JobDTO` padronizado permite adicionar fontes novas sem tocar no núcleo (Normalizer, banco, IA).
- **Modelo de dados já antecipa multiusuário**: `job_analysis` é modelada por par `(job_id, user_id)`, não por vaga isolada — decisão correta e fácil de esquecer se não fosse definida agora.
- **Regras de negócio explícitas e verificáveis**: "nunca notificar duas vezes", "nunca sobrescrever `job_analysis`", "nunca auto-apply sem confirmação" — funcionam como critérios de aceite automáticos para qualquer PR.
- **Deduplicação bem especificada**: chave `(source, external_id)` evita o erro mais comum em crawlers (vaga duplicada a cada execução do scheduler).
- **Contrato de saída da IA é estruturado e auditável**: score + recomendação + justificativa, com `raw_ai_response` armazenado para reprocessamento futuro — boa prática de engenharia de IA (nunca confiar só no score).
- **Segurança básica já correta**: segredos via `.env`, nunca no código.

### 1.2 Pontos Fracos

- **Nenhum código existe ainda** — todo o restante da análise é sobre risco de execução, não sobre bugs.
- **Documentação duplicada**: `architecture.md` e `architecture-JIA.md` são quase idênticos (o segundo é uma versão anterior sem o `User Context Engine`). Isso vai gerar confusão sobre qual é a fonte da verdade. Recomendo consolidar em um único arquivo e apagar o outro (ou arquivar) antes do Sprint 1.
- **Scheduler não tem tecnologia definida** — o diagrama mostra uma caixa "Scheduler", mas não há decisão entre cron do SO, `APScheduler` embutido no processo, ou execução via workflow externo (ex: GitHub Actions agendado). Isso afeta diretamente o design do `main.py`.
- **Migração de banco "manual" no MVP** (`migrations.py`) com plano de trocar para Alembic só na Fase 4 — isso é dívida técnica planejada desnecessariamente; Alembic funciona perfeitamente com SQLite desde o dia 1 e evita reescrever toda a camada de schema depois.
- **Nenhuma decisão sobre parsing de currículo** (`resume_parser.py`): currículo normalmente chega como PDF. Não há definição de biblioteca de extração de texto (`pypdf`/`pdfplumber`) nem de como a extração para JSON estruturado será feita (regras determinísticas vs. chamada à própria Claude API). Isso é ambíguo o suficiente para travar o Sprint 1 se não for decidido antes.
- **Sem estratégia de retry/backoff** definida para chamadas HTTP (crawler) nem para a Claude API — ambas podem falhar de forma transiente (rate limit, timeout).
- **Sem filtro determinístico antes da IA**: hoje, toda vaga coletada é enviada para análise via Claude. Sem um pré-filtro barato (localização, idioma, palavras-chave eliminatórias), o custo de IA cresce linearmente com o volume de vagas coletadas, mesmo para vagas obviamente incompatíveis.
- **Sem framework de teste explicitado** (`tests/` é mencionado, mas não `pytest` nem estratégia de mock para Playwright/HTTP).
- **Sem `.gitignore` definido** — risco real de commitar `data/database.sqlite` (contém currículo e dados pessoais de você e familiares) ou `.env`.

### 1.3 Riscos Técnicos

| Risco | Impacto | Mitigação recomendada |
|---|---|---|
| Playwright contra Greenhouse/Lever é mais frágil e lento do que necessário | Alto (Greenhouse e Lever expõem **APIs JSON públicas não autenticadas** — `boards-api.greenhouse.io` e `api.lever.co/v0/postings/{empresa}`) | Usar `httpx` direto para essas duas fontes; reservar Playwright só para fontes que exigem renderização JS real (ex: Workday em algumas configurações) |
| Workday tem proteção anti-bot conhecida | Médio — pode gerar bloqueio de IP ou CAPTCHA | Manter Workday como prioridade média/baixa; se necessário, avaliar via API interna do Workday antes de automação de navegador |
| Custo de chamadas à Claude API crescendo sem controle | Médio-Alto conforme volume de vagas aumenta | Introduzir pré-filtro determinístico (`relevance_filter`) antes de qualquer chamada à IA |
| SQLite sem backup e contendo dados pessoais (currículo, salário, família) | Médio — perda de dados ou vazamento se commitado por engano | `.gitignore` para `data/` desde o Sprint 1 + rotina simples de backup local (cópia do arquivo `.sqlite`) |
| Ambiguidade sobre parsing de currículo pode travar o Sprint 1 | Médio | Decidir agora: currículo pode ser cadastrado como JSON estruturado manualmente no MVP (`candidate_profile.json`); `resume_parser.py` (PDF → JSON via IA) fica para depois do Sprint 1, sem bloquear a fundação |
| Python 3.13 é recente — dependências (Playwright, SQLAlchemy) podem ter suporte incompleto | Baixo-Médio | Validar compatibilidade no Sprint 1 antes de travar versões no `requirements.txt` |
| `job_analysis` history crescendo indefinidamente sem nunca sobrescrever | Baixo no MVP, médio depois | Aceitável para MVP; revisar necessidade de retenção/expurgo na Fase 4 |

### 1.4 Melhorias Recomendadas

1. **Adotar Alembic desde o Sprint 1**, não só na Fase 4 — elimina reescrita futura de `migrations.py`.
2. **Usar `httpx` para Greenhouse e Lever** (APIs JSON públicas), reservando Playwright só para fontes que realmente exigem navegador — reduz fragilidade, custo de execução e risco de bloqueio.
3. **Config tipada via `pydantic-settings`** em vez de um `config.py` livre — falha rápido se uma variável de ambiente obrigatória estiver faltando.
4. **Pré-filtro determinístico antes da IA** (`services/relevance_filter.py`): elimina vagas obviamente fora do perfil (idioma, localização, cargo) antes de gastar uma chamada de IA — reduz custo e ruído.
5. **`tenacity` para retry/backoff** em chamadas HTTP e à Claude API.
6. **Logging estruturado** via módulo `logging` padrão do Python, configurado uma vez em `config.py`, com logger por módulo — nunca `print()`.
7. **Stack de testes**: `pytest` + `pytest-mock` + `respx` (mock de `httpx`) — permite testar crawlers sem rede real e sem abrir navegador de verdade nos testes.
8. **`.gitignore` desde o primeiro commit**, cobrindo `data/`, `.env`, `__pycache__/`, `.venv/`.
9. **Consolidar `architecture.md` e `architecture-JIA.md`** em um único documento antes do Sprint 1, para evitar deriva entre as duas versões.
10. **Gerenciamento de dependências reprodutível**: usar `uv` (ou `pip-tools`) com lockfile, não apenas `requirements.txt` solto — importante dado que Python 3.13 é recente e versões de dependências podem mudar rápido.

---

## 2. Plano de Desenvolvimento Incremental

> **Nota sobre numeração:** este plano reorganiza a Fase 1 (MVP) do `roadmap.md` em fases mais granulares (Fases 1–5 abaixo correspondem aos Sprints 1–5 do `roadmap.md`), e introduz a Fase 6 como preparação estrutural para a Fase 3 do `roadmap.md` (Multiusuário). As Fases 2 e 4 do `roadmap.md` original (mais crawlers/refino de prompts, e Plataforma SaaS) não são cobertas aqui — continuam como visão de longo prazo em `roadmap.md`.

### Fase 1 — Fundação do Projeto

**Objetivo:** ambiente Python funcional, estrutura de pastas e modelos iniciais de banco, sem nenhuma lógica de negócio ainda.

- Configuração Python 3.13 (virtualenv/`uv`), validação de compatibilidade das dependências principais.
- Estrutura de pastas conforme `architecture.md` §5 (`app/`, `data/`, `docs/`, `tests/`).
- Dependências principais: `sqlalchemy`, `alembic`, `pydantic-settings`, `python-dotenv`, `pytest`.
- Configuração de ambiente: `.env.example`, `.gitignore`, `config.py` tipado.
- Banco SQLite + Alembic configurado (não `migrations.py` manual).
- Modelos iniciais via SQLAlchemy: `User`, `Profile`, `Resume` (escopo do `roadmap.md` Sprint 1).

### Fase 2 — Motor de Coleta de Vagas

**Objetivo:** primeiro conector funcional entregando vagas normalizadas e deduplicadas.

- Arquitetura dos crawlers: `BaseCrawler` + `JobDTO` (`crawler-strategy.md`).
- Primeiro conector ATS: **Greenhouse**, via API JSON pública (`httpx`), não Playwright.
- `CrawlerRunner` simples para orquestrar execução (mesmo com um único crawler).
- Job Normalizer: validação + deduplicação por `(source, external_id)` antes de persistir.
- Tratamento de erro por crawler isolado (falha em uma fonte não derruba o processo).

### Fase 3 — Banco e Serviços

**Objetivo:** schema completo e camada de serviços/repositório estável para o restante do sistema.

- Models completos: `Job`, `JobAnalysis`, `Application`, `Notification` (`database-design.md`).
- Repository pattern sobre SQLAlchemy (`jobs_service.py`, `users_service.py`) — nenhuma query solta espalhada pelo código.
- Migrations Alembic incrementais para o schema completo.
- Tratamento de erros: validação antes de persistir (vaga sem `url`/`source` é rejeitada), constraints de unicidade (`(source, external_id)`).

### Fase 4 — Integração de IA

**Objetivo:** análise de compatibilidade real entre perfil e vaga, com score e justificativa.

- `context_builder.py` — User Context Engine consolidando `Resume` + `Profile`.
- Pré-filtro determinístico (melhoria recomendada, não estava no `roadmap.md` original) antes da chamada à IA.
- Integração com Claude API (`analyzer.py`, `prompts.py`).
- `scorer.py`: validação/normalização da resposta JSON, com fallback de reparsagem e retry via `tenacity`.
- Persistência em `job_analysis`, incluindo `raw_ai_response` para auditoria.

### Fase 5 — Notificações

**Objetivo:** usuário recebe, no Telegram, vagas relevantes sem esforço manual.

- Integração Telegram Bot API (`notifications/telegram.py`).
- Formatação de mensagem conforme exemplo em `architecture.md` §14.
- Regra de não duplicar notificação por `(user_id, job_id)`.
- Preferências do usuário: limite mínimo de score configurável para notificação.

**Critério de saída do MVP (Fases 1–5):** um usuário cadastrado recebe automaticamente, via Telegram, notificações de vagas relevantes com score e justificativa — sem nenhuma ação manual além do cadastro inicial de perfil e currículo. (Equivalente ao critério de saída da Fase 1 do `roadmap.md`.)

### Fase 6 — Preparação Multiusuário

**Objetivo:** garantir que a base construída nas Fases 1–5 já suporte múltiplos usuários reais (você, esposa, mãe) com isolamento de dados, antes de qualquer camada de cadastro/login mais sofisticada.

- Usuários: múltiplos registros reais em `users` (mesmo que cadastro ainda seja manual/via script, não via formulário público).
- Perfis profissionais: múltiplos perfis coexistindo sem interferência.
- Currículos: um currículo estruturado por usuário, sem mistura de contexto entre usuários.
- Preferências de busca: cada usuário com seu próprio limite de notificação, locais desejados, etc.
- Validação explícita de isolamento: nenhuma `job_analysis` ou `notification` pode vazar entre usuários (teste automatizado dedicado a isso).

> Cadastro/login formal (autenticação real, onboarding via formulário) permanece na Fase 3 do `roadmap.md` — fora do escopo desta Fase 6, que trata apenas da preparação estrutural de dados.

---

## 3. Sprint 1 — Fundação

### Objetivo

Ter um ambiente Python 3.13 funcional, com estrutura de pastas definitiva, banco SQLite versionado via Alembic, e os três primeiros modelos de dados (`User`, `Profile`, `Resume`) testados — sem nenhuma lógica de crawler, IA ou notificação ainda.

### Tasks

1. Consolidar `architecture.md` vs `architecture-JIA.md` (remover/arquivar a versão duplicada) antes de iniciar.
2. Criar ambiente virtual Python 3.13 e validar compatibilidade das dependências-alvo.
3. Criar `requirements.txt` (ou `pyproject.toml`) com: `sqlalchemy`, `alembic`, `pydantic-settings`, `pytest`, `black`.
4. Criar `.env.example` e `.gitignore` (cobrindo `data/`, `.env`, `__pycache__/`, `.venv/`).
5. Criar `app/config.py` com settings tipadas (`pydantic-settings`) lendo `.env`.
6. Criar `app/database/database.py` com engine/session SQLAlchemy apontando para `data/database.sqlite`.
7. Criar `app/database/models.py` com `User`, `Profile`, `Resume` conforme `database-design.md` §3.1–3.3.
8. Inicializar Alembic (`alembic init`) e gerar a primeira revision a partir dos models.
9. Escrever `README.md` inicial: visão geral, como configurar ambiente, como rodar migrations, link para `docs/`.
10. Escrever teste (`tests/test_models.py`) validando: criação de `User`, constraint de unicidade de `email`, criação de `Profile`/`Resume` vinculados a um `User`.

### Critério de Aceite

- [ ] `alembic upgrade head` cria `data/database.sqlite` com as tabelas `users`, `profiles`, `resumes` e nenhuma outra.
- [ ] `pytest` roda e passa (mínimo: teste de criação de `User` com sucesso + teste de violação de unicidade de `email`).
- [ ] Nenhum segredo, token ou caminho sensível commitado (`.env` e `data/` ignorados pelo git).
- [ ] `README.md` permite que qualquer pessoa clone o repositório e rode o projeto localmente seguindo só as instruções do arquivo.
- [ ] Código com type hints em 100% das funções novas, seguindo `development-guidelines.md`.
- [ ] Duplicidade `architecture.md`/`architecture-JIA.md` resolvida (arquivo único remanescente).

### Arquivos Criados

```
requirements.txt
.env.example
.gitignore
README.md
app/__init__.py
app/config.py
app/database/__init__.py
app/database/database.py
app/database/models.py
alembic.ini
migrations/env.py
migrations/versions/<timestamp>_initial_schema.py
tests/__init__.py
tests/test_models.py
data/.gitkeep
data/resumes/.gitkeep
```

---

## Próximos Passos

Este documento é só análise e planejamento — **nenhuma linha de código ou dependência foi instalada ainda**. Aguardando sua aprovação para:

1. Confirmar (ou ajustar) o escopo da Sprint 1 acima.
2. Decidir sobre a consolidação de `architecture.md`/`architecture-JIA.md`.
3. Iniciar a implementação incremental, testando cada task antes de avançar para a próxima, conforme `development-guidelines.md`.
