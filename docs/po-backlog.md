# PO Backlog — Bloqueios e Decisões Pendentes

**Como usar:** cada item abaixo é algo que depende de decisão ou ação da Clara para avançar de "scaffolding testado" para "uso real em produção". Nada aqui bloqueou o desenvolvimento — o código segue funcional e testado (54/54 testes passando).

---

## ✅ Resolvido — Modelo de IA trocado para Haiku (custo)

`app/ai/analyzer.py` usava `claude-sonnet-5`; trocado para `claude-haiku-4-5`. A tarefa (avaliar compatibilidade currículo x vaga com critérios explícitos no prompt) não exige o raciocínio mais caro do Sonnet. Estimativa de custo com o cenário que você descreveu (10 usuários, 30 vagas novas/dia, disparo às 08:00): **cada usuário recebe sua própria análise de cada vaga** (o custo é por análise, não por disparo) — 300 análises/dia × ~$0,0022 ≈ **$0,66/dia ≈ $20/mês no total** para os 10 usuários. Acompanhe o gasto real em console.anthropic.com/settings/usage depois de rodar por alguns dias — a estimativa assume ~1.200 tokens de entrada por análise, e descrições de vaga muito longas custam mais.

---

## ✅ Resolvido — Elegibilidade não podia ser hardcoded pro Brasil

**Achado real (bug):** `app/ai/prompts.py` tinha o texto "exclui o Brasil" fixo no código do critério eliminatório de elegibilidade — funcionava só por acidente pro seu caso anterior, mas quebraria assim que você (ou qualquer outro usuário) tivesse uma situação diferente. Corrigido para ser genérico: o critério agora referencia "nacionalidade, localização e situação de elegibilidade do candidato descritas no contexto", que vem do `Profile.summary` de cada usuário — funciona pra qualquer nacionalidade/situação, não só Brasil.

**Seu perfil atualizado** (você mencionou: indo pra Espanha, autorização de trabalho na UE só em fevereiro/2026, busca mundial):
- `requires_brazil_eligible` → `false` (não fazia mais sentido travar só no Brasil)
- `desired_locations` → adicionado `Worldwide` e `Spain`
- `summary` → adicionei a frase explicando sua situação (cidadã brasileira, se mudando pra Espanha, sem autorização UE ainda, busca vagas remotas mundiais que não exijam autorização de um país específico que você não tem)

## 📌 Sinal de produto a validar com você (não implementei nada ainda)

Você comentou: *"pode ser que pessoas comprem esse produto... podem estar em qualquer lugar do mundo e quererem vagas de qualquer lugar do mundo"*. Isso é maior que o escopo atual (hoje é 1 perfil por env vars/Secrets, pensado pra você + família — ver `product-requirements.md`, "Fase inicial: uso pessoal"). Se a intenção é virar um produto vendável pra terceiros, isso é a Fase 3/4 do `roadmap.md` (Multiusuário/SaaS: cadastro próprio, login self-service, billing) — um salto de arquitetura real, não um ajuste pequeno. Não comecei a construir isso sem confirmar com você primeiro. Quando quiser, me diga se é pra eu já escopar isso como próxima iniciativa grande.

---

## ✅ Resolvido — Frontend (login + backoffice de acesso)

Implementado em `app/web/`: tela de login e backoffice onde um admin cria acesso para novos usuários (gera senha temporária, mostrada uma única vez) e revoga/restaura acesso sem apagar o histórico da pessoa. Testado com 10 testes automatizados + verificação visual real no navegador (desktop e mobile 375px — tabela vira lista de cards no mobile, sem scroll horizontal).

**Decisão técnica: FastAPI + Jinja2 (server-rendered), não React/Next.js.** O resto do projeto é 100% Python; duas telas não justificam introduzir um toolchain JS/Node separado (build, bundler, etc.) — FastAPI + templates HTML com CSS responsivo (mobile-first, sem framework CSS externo) entrega o mesmo resultado com uma stack só, mais simples de manter. Se o produto crescer bastante (dashboard complexo, muitas telas), migrar para uma SPA pode valer a pena — não é o caso hoje.

**Segurança implementada:** senha com `bcrypt` (nunca texto puro), cookie de sessão assinado (`itsdangerous`, expira em 14 dias, `httponly` + `samesite=lax`), admin não consegue revogar o próprio acesso (evita lockout). **Simplificação assumida:** sem proteção CSRF explícita — risco baixo para uso pessoal/familiar (poucos usuários, sem conteúdo de terceiros), mas se isso virar algo maior/público, precisa de hardening antes.

**🔴 Ação sua — falta decidir onde hospedar.** GitHub Actions (usado para a busca diária) só roda tarefas agendadas — não serve para manter um site no ar o tempo todo. Preciso que você escolha:
- **Railway** — você já tem conta (projeto ARS/PICC), mas seria um projeto novo e separado lá, com custo próprio; ou
- **Render / Fly.io** — têm free tier para apps pequenos, conta nova seria necessária.

Não criei conta em nenhum desses por você (decisão de custo/plataforma que só você pode tomar). O app roda localmente hoje via `uv run uvicorn app.web.app:app` — assim que escolher a plataforma, é um deploy direto (Dockerfile pode ser adicionado se necessário).

**Como criar o primeiro admin (você) depois de hospedar:** ainda não existe uma tela de "primeiro acesso" — defina manualmente `is_admin=True` e uma senha (`app.web.security.hash_password`) no seu usuário via script, do mesmo jeito que fiz para testar localmente. Se preferir, posso construir uma tela/CLI de bootstrap do primeiro admin — me avise.

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

(`USER_NAME`, `USER_EMAIL`, `PROFILE_JSON`, `RESUME_JSON` e `SESSION_SECRET_KEY` já estão configurados — não precisa mexer, a menos que queira corrigir algo do perfil.)

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
- Scheduler — `daily-run.yml` (diário) + `seed-user.yml` (cadastro, via Secrets) — únicos workflows mantidos, pra minimizar consumo de Actions. `dependabot.yml` mantém dependências atualizadas (não consome minutos de Actions, é um serviço à parte). Testes/lint rodam localmente antes de cada commit (`uv run pytest` + `uv run black`), não em CI.
- Seu perfil real já está nos Secrets do repositório, testado localmente.
- Frontend — `app/web/` (login + backoffice de acesso), responsivo, testado e verificado visualmente.

**54/54 testes passando, `black` sem alterações necessárias.**
