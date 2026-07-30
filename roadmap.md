# Roadmap

**Produto:** Job Intelligence Agent

---

## Fase 1 — MVP

### Sprint 1 — Fundação
- Estrutura do projeto Python (pastas, `requirements.txt`, `.env`, `config.py`).
- Configuração de ambiente (virtualenv, dependências: Playwright, SQLAlchemy, etc.).
- `README.md` inicial.
- Modelo de dados base (`users`, `profiles`, `resumes`) via SQLAlchemy.

### Sprint 2 — Crawler
- Implementar `BaseCrawler` e `JobDTO` (ver `crawler-strategy.md`).
- Implementar primeiro conector: **Greenhouse**.
- Job Normalizer com deduplicação por `(source, external_id)`.

### Sprint 3 — Banco de Dados
- Finalizar schema completo (`jobs`, `job_analysis`, `applications`, `notifications`).
- Migrations iniciais (`migrations.py`).
- Popular banco com dados reais de teste via crawler do Sprint 2.

### Sprint 4 — Inteligência Artificial
- Implementar `User Context Engine` (`context_builder.py`).
- Integração com Claude API (`analyzer.py`, `prompts.py`, `scorer.py`).
- Geração de score + recomendação + justificativa por vaga.

### Sprint 5 — Telegram
- Integração com Telegram Bot API.
- Notificação formatada (ver exemplo em `architecture.md`).
- Regra de não duplicar notificação para a mesma vaga/usuário.

**Critério de saída do MVP:** um usuário cadastrado recebe, automaticamente, notificações de vagas relevantes no Telegram, com score e justificativa, sem nenhuma ação manual além do cadastro inicial de perfil e currículo.

---

## Fase 2 — Consolidação da IA

- Adicionar segundo e terceiro crawlers (**Lever**, depois **Ashby**/**Workday**).
- Refinar prompts com base em análises reais (feedback qualitativo).
- Introduzir histórico simples de interação do usuário (aplicou / ignorou) para começar a alimentar o `User Context Engine`.
- Testes automatizados cobrindo `scorer.py` e `context_builder.py`.

---

## Fase 3 — Multiusuário

- Cadastro e login (múltiplos usuários reais, não apenas registros manuais no banco).
- Perfis individuais completos, com múltiplos currículos por usuário (opcional: currículo por tipo de vaga).
- Isolamento de dados entre usuários (garantir que `job_analysis` e `notifications` nunca vazem entre contas).
- Ajustes de UX no fluxo de cadastro (ex: onboarding via Telegram ou formulário simples).

---

## Fase 4 — Plataforma SaaS

- Dashboard web (histórico de vagas, análises, candidaturas).
- Métricas de uso (vagas notificadas, taxa de relevância, tempo de resposta).
- Gestão de candidaturas (status: `applied`, `interview`, `rejected`, `offer`).
- Migração de SQLite → PostgreSQL (ver `database-design.md`, seção 5).
- Possível introdução de billing/planos (fora do escopo até esta fase).

---

## Visão Resumida

```
Fase 1 (MVP)
 ├─ Sprint 1: Fundação
 ├─ Sprint 2: Crawler
 ├─ Sprint 3: Banco
 ├─ Sprint 4: IA
 └─ Sprint 5: Telegram

Fase 2 (Consolidação da IA)
 ├─ Mais crawlers
 ├─ Refino de prompts
 └─ Histórico de interação

Fase 3 (Multiusuário)
 ├─ Cadastro/Login
 ├─ Perfis individuais
 └─ Currículos múltiplos

Fase 4 (SaaS)
 ├─ Dashboard web
 ├─ Métricas
 ├─ Gestão de candidaturas
 └─ PostgreSQL
```
