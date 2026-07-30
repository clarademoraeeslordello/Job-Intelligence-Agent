# PO Backlog — Bloqueios e Decisões Pendentes

**Gerado em:** desenvolvimento contínuo das Fases 2–6 (ver `docs/development-plan.md`).
**Como usar:** cada item abaixo é algo que **depende de decisão da Clara** para avançar de "scaffolding testado" para "uso real em produção". Nada aqui bloqueou o desenvolvimento — o código segue funcional e testado (29/29 testes passando) com comportamento degradado documentado em cada ponto.

---

## 1. Lista de empresas Greenhouse a rastrear (decisão de produto)

**Status:** bloqueado — precisa da sua decisão.

`GreenhouseCrawler` está implementado e testado, mas o Greenhouse não tem busca global — cada empresa tem seu próprio "board token" (ex: `spotify`, `notion`). Hoje isso é lido de `GREENHOUSE_BOARD_TOKENS` no `.env` (vazio por padrão). `app/main.py` já loga um aviso claro e não quebra se estiver vazio.

**Preciso de:** lista inicial de empresas/board tokens que você quer rastrear (pode ser 2-3 para começar). O board token normalmente aparece na URL pública da vaga: `boards.greenhouse.io/<board_token>/jobs/...`.

## 2. Credenciais reais (CLAUDE_API_KEY, TELEGRAM_TOKEN)

**Status:** bloqueado — nenhuma chave real disponível nesta máquina/sessão.

Todo o motor de IA (`app/ai/`) e de notificação (`app/notifications/telegram.py`) está implementado e testado com clients mockados (nenhuma chamada real de API nos testes). Para rodar `app/main.py` de ponta a ponta de verdade, faltam:

- `CLAUDE_API_KEY` — chave da Claude API (console.anthropic.com).
- `TELEGRAM_TOKEN` — token de bot criado via [@BotFather](https://t.me/BotFather), e o `telegram_chat_id` de cada usuário cadastrado.

Sem essas chaves, `run_once()` executa a coleta de vagas normalmente e para antes da análise/notificação (com log de aviso), sem quebrar.

## 3. Tecnologia de scheduler ainda não decidida

**Status:** pendente de decisão, não bloqueia o MVP.

`docs/development-plan.md` já apontava isso como risco. Hoje existe só `app/main.py` como entrypoint manual (`python -m app.main`). Opções para decidir depois:

- Cron do SO (Windows Task Scheduler / cron no Linux, se migrar para um servidor).
- `APScheduler` embutido no próprio processo Python (roda continuamente).
- Execução agendada via GitHub Actions (mais simples de operar, sem servidor próprio).

**Preciso de:** onde/como você pretende rodar isso continuamente (sua máquina sempre ligada? um servidor? GitHub Actions?) para escolher a opção certa.

## 4. `resume_parser.py` (PDF → JSON) não implementado

**Status:** adiado intencionalmente, não bloqueia.

A Sprint 1 assumiu cadastro manual do currículo estruturado (`Resume.structured_json`), conforme `architecture.md` (`candidate_profile.json`). Parsing automático de PDF (via `pypdf`/`pdfplumber` + extração assistida por IA) não foi implementado — não estava no escopo de nenhuma fase até agora e não bloqueia o MVP, já que o currículo pode ser inserido como JSON diretamente.

**Preciso de:** confirmar se isso entra como Fase 7 (ou parte da Fase 3 do `roadmap.md`, "Multiusuário") antes de eu implementar.

## 5. Nome de exibição da empresa (Greenhouse)

**Status:** simplificação técnica, não bloqueia.

`GreenhouseCrawler` usa o `board_token` como `company` (ex: `"spotify"`) em vez do nome de exibição real. O nome real está disponível via `GET /v1/boards/{token}` (endpoint separado), não implementado ainda por ser um refinamento de baixa prioridade frente ao restante do MVP.

## 6. Decisão técnica: Telegram via `httpx` direto, não `python-telegram-bot`

**Status:** decisão já tomada, só documentando.

O SDK oficial `python-telegram-bot` é assíncrono (`asyncio`), o que introduziria inconsistência num codebase majoritariamente síncrono. Implementei `TelegramNotifier` com chamada HTTP direta via `httpx` (mesma biblioteca já usada nos crawlers), testável com `respx` sem rede real. Dependência `python-telegram-bot` removida do `pyproject.toml`.

---

## Resumo do que já está pronto e testado (sem depender dos itens acima)

- Fase 2 — Crawler engine (`BaseCrawler`, `JobDTO`, `GreenhouseCrawler`, `CrawlerRunner`, dedup).
- Fase 3 — Schema completo (`Job`, `JobAnalysis`, `Application`, `Notification`) + `JobsService`.
- Fase 4 — `context_builder`, `prompts`, `analyzer`, `scorer` — testado com client Claude mockado.
- Fase 5 — `telegram.py` + `notification_service.py` — dedup por `(user_id, job_id)`, threshold de score configurável por perfil, testado com client Telegram mockado.
- Fase 6 — teste dedicado (`test_multiuser_isolation.py`) comprovando que `JobAnalysis` e `Notification` nunca vazam entre usuários.

**29/29 testes passando, `black` sem alterações necessárias.**
