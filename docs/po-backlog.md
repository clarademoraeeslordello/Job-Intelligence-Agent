# PO Backlog — Bloqueios e Decisões Pendentes

**Como usar:** cada item abaixo é algo que depende de decisão ou ação da Clara para avançar de "scaffolding testado" para "uso real em produção". Nada aqui bloqueou o desenvolvimento — o código segue funcional e testado (38/38 testes passando).

---

## ✅ Resolvido — Busca abrangente (sem lista de empresas)

Duas fontes agregadoras rodam sempre, sem precisar de configuração:

- `ArbeitnowCrawler` (`app/crawler/arbeitnow.py`) — API pública, vagas de múltiplas fontes/países.
- `RemoteOKCrawler` (`app/crawler/remoteok.py`) — API pública, 100% focada em vagas remotas (adicionada depois que você confirmou que quer só remoto).

Ambas filtram para trazer só vagas publicadas nas últimas 48h (folga de 48h em vez de 24h para tolerar atraso entre execuções diárias sem perder vaga). `GreenhouseCrawler` continua existindo, mas é opcional (só roda se você configurar `GREENHOUSE_BOARD_TOKENS`).

**Limitação a saber:** LinkedIn e Indeed não têm API pública aberta e bloqueiam scraping — não estão nas fontes. "Bem abrangente" aqui significa múltiplas fontes públicas somadas, não uma fonte única universal.

## ✅ Resolvido — Tecnologia de scheduler

**GitHub Actions**, confirmado por você. `.github/workflows/daily-run.yml`, todo dia às 09:00 UTC (06:00 BRT), ou manual (aba **Actions** → **Busca diaria de vagas** → **Run workflow**). Banco SQLite persiste entre execuções via `actions/cache` (nunca commitado no git — repo é público e o banco guarda currículo/salário).

## ✅ Resolvido — Critérios de elegibilidade (a partir do seu currículo)

Você pediu: remoto, inglês intermediário, aceita brasileiros, CLT ou PJ. Implementei:

- `Profile.employment_types` (novo campo) — tipos de contratação aceitos (`CLT`, `PJ`, `Cooperativa` — mantive os termos brasileiros no dado, mas o prompt da IA explica a equivalência internacional: CLT ~ full-time employment, PJ ~ independent contractor/freelance).
- `Profile.requires_brazil_eligible` (novo campo, `True` no seu perfil) — instrui a IA a marcar como `IGNORE` vagas remotas explicitamente restritas a candidatos de outro país/região.
- `app/ai/prompts.py` — critérios eliminatórios: nível de inglês exigido acima do seu (intermediário) só derruba a vaga se for requisito **explícito e obrigatório** (não aplica a "diferencial"); tipo de contratação só derruba se a vaga for **explícita** sobre isso (a maioria não é).

Migration aplicada localmente (`183219bc0847` → `da4baa756e6d`).

## ✅ Resolvido — Seu perfil já está cadastrado

Li seu currículo (`Clara de Moraes Lordello.pdf`, anexado por você) e criei os secrets `USER_NAME`, `USER_EMAIL`, `PROFILE_JSON` e `RESUME_JSON` diretamente no repositório (via `gh secret set` — nunca aparecem em log nem no código). Testei localmente rodando `python -m app.seed` com esses mesmos dados — funcionou, usuário criado com `employment_types=['CLT', 'PJ', 'Cooperativa']`, `requires_brazil_eligible=True`, 43 skills extraídas do currículo.

**Importante — isso ainda não está no ambiente do GitHub Actions.** O banco local (`data/database.sqlite`, na sua máquina) e o banco cacheado no GitHub Actions são arquivos diferentes. Assim que você criar `CLAUDE_API_KEY` e `TELEGRAM_TOKEN` (únicos itens que faltam, ver abaixo), rode o workflow **Cadastrar/atualizar usuario** uma vez (aba Actions) para popular o banco de produção com o mesmo perfil.

Se algo no seu perfil ficou errado ou incompleto (nível de senioridade, expectativa salarial não perguntei, cargo, etc.), me avise que eu ajusto o secret.

## 🔴 Ação sua — As 3 únicas coisas que faltam

Não posso criar nenhuma dessas por você (contas/credenciais pessoais).

### 1. Claude API Key
1. [console.anthropic.com](https://console.anthropic.com) → login/cadastro → **API Keys** → **Create Key**.
2. Copie a chave.

### 2. Telegram Bot Token
1. No Telegram, fale com **@BotFather** → `/newbot` → escolha nome e username (termina em `bot`).
2. Ele devolve um token `123456:ABC-DEF...`.

### 3. Seu Telegram Chat ID
1. No Telegram, fale com **@userinfobot** → ele responde na hora com seu `chat_id`.
2. Se sua mãe/esposa forem usar depois, cada uma repete esse passo e também precisa iniciar conversa com o bot criado no passo 2 (exigência de segurança do Telegram).

### Cadastrar como GitHub Secrets

**Settings → Secrets and variables → Actions → Secrets**, adicionar:

| Nome | Valor |
|---|---|
| `CLAUDE_API_KEY` | chave do passo 1 |
| `TELEGRAM_TOKEN` | token do passo 2 |
| `USER_TELEGRAM_CHAT_ID` | chat_id do passo 3 |

(`USER_NAME`, `USER_EMAIL`, `PROFILE_JSON`, `RESUME_JSON` já estão configurados — não precisa mexer, a menos que queira corrigir algo do perfil.)

### Depois disso

Aba **Actions** → **Cadastrar/atualizar usuario** → **Run workflow** (uma vez, popula o banco de produção). A partir daí, `daily-run.yml` já roda sozinho todo dia e te notifica no Telegram quando o score passar de 75 (seu `notification_score_threshold`).

---

## Pendências de menor prioridade (não bloqueiam)

### `resume_parser.py` (PDF → JSON automático) não implementado

Seu currículo eu li manualmente e estruturei no `RESUME_JSON`. Um parser automático (PDF → texto → JSON via IA) seria útil se sua mãe/esposa forem usar depois e você não quiser fazer esse trabalho manual de novo — fica como próximo passo natural, não bloqueia seu uso agora.

### Nome de exibição da empresa (Greenhouse)

Só relevante se você um dia configurar `GREENHOUSE_BOARD_TOKENS`. Baixa prioridade.

### Telegram via `httpx` direto, não `python-telegram-bot`

Decisão técnica já tomada: SDK oficial é assíncrono, quebraria a consistência do codebase síncrono.

---

## Resumo do que já está pronto e testado

- Fase 2 — `BaseCrawler`, `JobDTO`, `ArbeitnowCrawler`, `RemoteOKCrawler`, `GreenhouseCrawler`, `CrawlerRunner`, dedup.
- Fase 3 — Schema completo (`Job`, `JobAnalysis`, `Application`, `Notification`) + `JobsService`.
- Fase 4 — `context_builder`, `prompts` (com critérios de elegibilidade), `analyzer`, `scorer` — testado com client Claude mockado.
- Fase 5 — `telegram.py` + `notification_service.py` — dedup, threshold configurável — testado com client mockado.
- Fase 6 — teste dedicado (`test_multiuser_isolation.py`) comprovando isolamento entre usuários.
- Scheduler — `daily-run.yml` (diário) + `seed-user.yml` (cadastro, via Secrets).
- CI — `.github/workflows/ci.yml` roda testes + lint em todo push/PR; `dependabot.yml` mantém dependências atualizadas.
- Seu perfil real já está nos Secrets do repositório, testado localmente.

**38/38 testes passando, `black` sem alterações necessárias.**
