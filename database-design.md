# Database Design

**Produto:** Job Intelligence Agent
**MVP:** SQLite | **Futuro:** PostgreSQL | **ORM:** SQLAlchemy

---

## 1. Entidades

- `User`
- `Profile`
- `Resume`
- `Job`
- `JobAnalysis`
- `Application`
- `Notification`

---

## 2. Diagrama de Relacionamento (visão lógica)

```
User (1) ──── (1) Profile
User (1) ──── (1) Resume
User (1) ──── (N) Application
User (1) ──── (N) Notification

Job  (1) ──── (N) JobAnalysis
Job  (1) ──── (N) Application

Application (N) ──── (1) User
Application (N) ──── (1) Job

JobAnalysis (N) ──── (1) Job
JobAnalysis (N) ──── (1) User   -- análise é sempre relativa a um usuário específico
```

Resumo textual:

```
User
 |
 +-- Profile
 |
 +-- Resume
 |
 +-- Applications ── Jobs
 |
 +-- Notifications

Job
 |
 +-- JobAnalysis (por usuário)
 |
 +-- Applications
```

> Ponto de atenção: `JobAnalysis` é sempre **por par (usuário, vaga)** — a mesma vaga pode ter scores diferentes para usuários diferentes, já que o contexto (currículo, preferências) muda. Isso é essencial para o modelo multiusuário.

---

## 3. Tabelas

### 3.1 `users`

| Campo              | Tipo      | Observações                  |
|---------------------|-----------|-------------------------------|
| id                  | INTEGER PK| |
| name                | TEXT      | |
| email               | TEXT      | único |
| telegram_chat_id    | TEXT      | usado para notificações |
| created_at          | DATETIME  | |

### 3.2 `profiles`

| Campo              | Tipo      | Observações |
|---------------------|-----------|--------------|
| id                  | INTEGER PK | |
| user_id             | INTEGER FK → users.id | |
| headline            | TEXT | ex: "Product Manager Sênior" |
| summary             | TEXT | resumo profissional |
| years_experience    | INTEGER | |
| desired_roles       | TEXT (JSON list) | ex: ["Product Manager", "PO"] |
| desired_locations   | TEXT (JSON list) | ex: ["Suécia", "Remoto"] |
| languages           | TEXT (JSON list) | ex: ["Português", "Inglês"] |
| salary_expectation  | TEXT | pode ser faixa ou valor |
| remote_preference   | TEXT | enum: `remote`, `hybrid`, `onsite`, `any` |

### 3.3 `resumes`

Armazena o currículo estruturado (ver também `candidate_profile.json` em `architecture.md`).

| Campo         | Tipo      | Observações |
|----------------|-----------|--------------|
| id             | INTEGER PK | |
| user_id        | INTEGER FK → users.id | |
| raw_file_path  | TEXT | caminho do PDF original, se houver |
| structured_json| TEXT (JSON) | skills, experience, education, languages |
| updated_at     | DATETIME | |

### 3.4 `jobs`

| Campo         | Tipo      | Observações |
|----------------|-----------|--------------|
| id             | INTEGER PK | |
| title          | TEXT | |
| company        | TEXT | |
| location       | TEXT | |
| country        | TEXT | |
| remote         | BOOLEAN | |
| salary         | TEXT | nem toda vaga informa salário |
| description    | TEXT | |
| requirements   | TEXT | |
| url            | TEXT | única por fonte |
| source         | TEXT | ex: "greenhouse", "lever" |
| external_id    | TEXT | ID da vaga na fonte original, usado para deduplicação |
| created_at     | DATETIME | |

> Índice único recomendado: (`source`, `external_id`) — evita vaga duplicada mesmo que o crawler rode múltiplas vezes.

### 3.5 `job_analysis`

| Campo         | Tipo      | Observações |
|----------------|-----------|--------------|
| id             | INTEGER PK | |
| job_id         | INTEGER FK → jobs.id | |
| user_id        | INTEGER FK → users.id | |
| score          | FLOAT | 0–100 |
| recommendation | TEXT | enum: `APPLY`, `ANALYZE`, `IGNORE` |
| positive_points| TEXT (JSON list) | |
| negative_points| TEXT (JSON list) | |
| raw_ai_response| TEXT (JSON) | resposta completa da IA, para auditoria/debug |
| created_at     | DATETIME | |

### 3.6 `applications`

| Campo         | Tipo      | Observações |
|----------------|-----------|--------------|
| id             | INTEGER PK | |
| user_id        | INTEGER FK → users.id | |
| job_id         | INTEGER FK → jobs.id | |
| status         | TEXT | enum: `not_applied`, `applied`, `interview`, `rejected`, `offer` |
| applied_at     | DATETIME | nullable |
| notes          | TEXT | anotações do usuário |

### 3.7 `notifications`

| Campo         | Tipo      | Observações |
|----------------|-----------|--------------|
| id             | INTEGER PK | |
| user_id        | INTEGER FK → users.id | |
| job_id         | INTEGER FK → jobs.id | |
| channel        | TEXT | ex: "telegram" |
| sent_at        | DATETIME | |
| status         | TEXT | enum: `sent`, `failed` |

---

## 4. Regras de Integridade

- Uma vaga (`jobs`) nunca deve ser inserida duas vezes com o mesmo `(source, external_id)`.
- Uma `job_analysis` só deve ser gerada uma vez por par `(job_id, user_id)`, exceto se o perfil do usuário mudar (nesse caso, gerar nova análise e manter histórico, não sobrescrever).
- Uma `notification` só deve ser criada se ainda não existir notificação para o mesmo `(user_id, job_id)`.
- Toda tabela sensível a auditoria (`job_analysis`, `notifications`, `applications`) deve manter `created_at`/`sent_at` para rastreabilidade.

---

## 5. Migração para PostgreSQL (futuro)

Ao migrar de SQLite para PostgreSQL (Fase 4 — SaaS):

- Trocar campos `TEXT (JSON)` por tipo nativo `JSONB` para permitir queries mais eficientes sobre skills, preferências, etc.
- Adicionar índices em `jobs.source`, `jobs.created_at` e `job_analysis.score` para suportar dashboards e filtros.
- Usar migrations versionadas via Alembic (compatível com SQLAlchemy) em vez do `migrations.py` manual do MVP.
