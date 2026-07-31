# PO Backlog — Bloqueios e Decisões Pendentes

**Como usar:** cada item abaixo é algo que depende de decisão ou ação da Clara para avançar de "scaffolding testado" para "uso real em produção". Nada aqui bloqueou o desenvolvimento — o código segue funcional e testado (35/35 testes passando).

---

## ✅ Resolvido — Busca abrangente (sem lista de empresas)

Você não quer curar uma lista de empresas — quer cobertura ampla, sem esforço manual. `GreenhouseCrawler` continua existindo (útil se um dia você quiser rastrear uma empresa específica), mas o crawler principal agora é `ArbeitnowCrawler` (`app/crawler/arbeitnow.py`): API pública e gratuita, sem autenticação, que agrega vagas de múltiplas fontes/países, sem precisar de nenhuma configuração. Ele já filtra automaticamente para trazer só vagas publicadas nas últimas 48h (`lookback_hours=48` — a folga de 48h em vez de 24h é para tolerar atraso entre execuções diárias sem perder vaga). Roda sempre, incondicionalmente, em `app/main.py`.

**Limitação a saber:** nenhuma fonte agregadora cobre 100% do mercado (LinkedIn e Indeed, por exemplo, não têm API pública aberta e bloqueiam scraping agressivamente — por isso não estão nas fontes). Cobertura "bem abrangente" aqui significa múltiplas fontes públicas somadas ao longo do tempo, não uma fonte única universal. Se quiser, dá pra somar mais agregadores depois (ex: RemoteOK).

## ✅ Resolvido — Tecnologia de scheduler

**GitHub Actions**, confirmado por você — gratuito (repo público), roda na nuvem, não depende do seu PC ligado. Implementado em `.github/workflows/daily-run.yml`, agendado para rodar todo dia às 09:00 UTC (06:00 horário de Brasília). Pode ser disparado manualmente também (aba **Actions** → **Busca diaria de vagas** → **Run workflow**).

**Decisão técnica importante:** o banco SQLite não pode ser commitado no git (repo é público, e o banco guarda currículo/salário/dados pessoais — commitar isso no histórico do git seria um vazamento permanente). Em vez disso, o banco persiste entre execuções via `actions/cache` (armazenamento interno do GitHub Actions, não navegável publicamente, nunca aparece no código-fonte do repositório).

## 🔴 Ação sua — Criar as credenciais

Nenhuma dessas eu posso criar por você (são contas/chaves pessoais). Passo a passo:

### 1. Claude API Key

1. Acesse [console.anthropic.com](https://console.anthropic.com) e faça login/cadastro.
2. Vá em **API Keys** → **Create Key**.
3. Copie a chave (só aparece uma vez).

### 2. Telegram Bot Token

1. No Telegram, procure **@BotFather** e inicie uma conversa.
2. Envie `/newbot`, escolha um nome e um username (precisa terminar em `bot`, ex: `job_intelligence_clara_bot`).
3. O BotFather devolve um token no formato `123456:ABC-DEF...` — isso é o `TELEGRAM_TOKEN`.

### 3. Telegram Chat ID (seu e de quem mais for usar)

1. No Telegram, procure **@userinfobot** e inicie uma conversa com ele — ele responde na hora com seu `chat_id` (um número).
2. Repita para cada pessoa que vai usar (você, sua mãe, sua esposa) — cada uma precisa iniciar uma conversa com o bot que você criou no passo 2 antes de poder receber mensagens dele (o Telegram exige isso por segurança).

### 4. Cadastrar tudo como GitHub Secrets/Variables (nunca no código ou no `.env` commitado)

No repositório, vá em **Settings → Secrets and variables → Actions**.

**Em "Secrets" (valores nunca aparecem em log, nem pra você depois de salvos):**

| Nome | Valor |
|---|---|
| `CLAUDE_API_KEY` | a chave do passo 1 |
| `TELEGRAM_TOKEN` | o token do passo 2 |
| `USER_NAME` | seu nome |
| `USER_EMAIL` | seu email |
| `USER_TELEGRAM_CHAT_ID` | seu chat_id do passo 3 |
| `PROFILE_JSON` | ver formato abaixo |
| `RESUME_JSON` | ver formato abaixo |

**Em "Variables" (não sensível, pode aparecer em log):**

| Nome | Valor |
|---|---|
| `GREENHOUSE_BOARD_TOKENS` | opcional, vazio por padrão |

**Formato de `PROFILE_JSON`** (todos os campos opcionais):
```json
{
  "headline": "Product Manager Senior",
  "summary": "8 anos de experiencia em produtos B2B SaaS",
  "years_experience": 8,
  "desired_roles": ["Product Manager", "Head of Product"],
  "desired_locations": ["Remoto", "Suecia"],
  "languages": ["Portugues", "Ingles"],
  "salary_expectation": "€60k-80k",
  "remote_preference": "remote",
  "notification_score_threshold": 75
}
```

**Formato de `RESUME_JSON`:**
```json
{
  "skills": ["product management", "sql", "figma"],
  "experience": [{"empresa": "...", "cargo": "...", "periodo": "..."}],
  "education": [{"curso": "...", "instituicao": "..."}],
  "languages": ["Portugues nativo", "Ingles fluente"]
}
```

### 5. Rodar o cadastro

Depois de salvar os secrets: aba **Actions** → **Cadastrar/atualizar usuario** → **Run workflow**. Roda uma vez, cria seu usuário no banco. Repita sempre que quiser atualizar perfil/currículo (é upsert — não duplica).

Depois disso, `daily-run.yml` já vai te notificar automaticamente todo dia, se houver vaga com score acima do seu `notification_score_threshold`.

---

## Pendências de menor prioridade (não bloqueiam)

### `resume_parser.py` (PDF → JSON) não implementado

Hoje o currículo entra como JSON estruturado (`RESUME_JSON`, ver acima), preenchido manualmente. Parsing automático de PDF fica pra depois — não bloqueia o uso real, só exige que você monte o JSON uma vez.

### Nome de exibição da empresa (Greenhouse)

`GreenhouseCrawler` (usado só se você configurar `GREENHOUSE_BOARD_TOKENS`) usa o board token como nome da empresa em vez do nome real. Baixa prioridade.

### Telegram via `httpx` direto, não `python-telegram-bot`

Decisão técnica já tomada: o SDK oficial é assíncrono, o que quebraria a consistência do codebase síncrono. `TelegramNotifier` usa `httpx` direto (mesma lib dos crawlers), testável sem rede real.

---

## Resumo do que já está pronto e testado

- Fase 2 — Crawler engine (`BaseCrawler`, `JobDTO`, `GreenhouseCrawler`, `ArbeitnowCrawler`, `CrawlerRunner`, dedup).
- Fase 3 — Schema completo (`Job`, `JobAnalysis`, `Application`, `Notification`) + `JobsService`.
- Fase 4 — `context_builder`, `prompts`, `analyzer`, `scorer` — testado com client Claude mockado.
- Fase 5 — `telegram.py` + `notification_service.py` — dedup, threshold configurável — testado com client mockado.
- Fase 6 — teste dedicado (`test_multiuser_isolation.py`) comprovando isolamento entre usuários.
- Scheduler — `.github/workflows/daily-run.yml` (diário) + `seed-user.yml` (cadastro manual, dados sensíveis via Secrets).

**35/35 testes passando, `black` sem alterações necessárias.**
