# Job Intelligence Agent — Arquitetura

**Versão:** 1.0

---

## 1. Visão Geral

### Objetivo

Criar um agente inteligente de busca de vagas utilizando Python, automação web e Inteligência Artificial.

O sistema será capaz de:

- Buscar vagas automaticamente em diferentes fontes.
- Analisar oportunidades com base no perfil profissional do usuário.
- Classificar compatibilidade entre candidato e vaga.
- Enviar recomendações personalizadas.
- Evoluir futuramente para uma plataforma multiusuário.

---

## 2. Visão do Produto

O Job Intelligence Agent deve funcionar como um recrutador pessoal baseado em IA.

O sistema deverá:

1. Entender o perfil profissional do usuário.
2. Buscar oportunidades compatíveis.
3. Avaliar requisitos da vaga.
4. Gerar uma pontuação de compatibilidade.
5. Recomendar ações.
6. Notificar o usuário.

---

## 3. Arquitetura Inicial

Fluxo principal:

```
Scheduler
  |
  v
Python Application
  |
  +--> ATS Crawlers
  |
  +--> Playwright Automation
  |
  v
Job Normalizer
  |
  v
SQLite Database
  |
  v
User Context Engine  <-- currículo + perfil + preferências do usuário
  |
  v
Claude AI Engine
  |
  v
Telegram Notification
```

> **Nota de arquitetura:** o **User Context Engine** foi adicionado como uma camada explícita entre o banco de dados e a IA. Ele é responsável por consolidar currículo, perfil e preferências do usuário antes de cada análise. Esse é o verdadeiro diferencial do produto — não "achar vagas" (isso já existe em toda plataforma de emprego), mas conhecer profundamente o usuário para filtrar o que realmente importa. Ver detalhes em `ai-engine.md`.

---

## 4. Stack Tecnológica

### Backend

- Python 3.13

### Automação

- Playwright

Responsável por:
- Navegação automática.
- Coleta de vagas.
- Extração de informações.

### Banco de Dados

- **MVP:** SQLite
- **Futuro:** PostgreSQL
- **ORM:** SQLAlchemy

### Inteligência Artificial

- Claude API

Responsável por:
- Análise das vagas.
- Ranking.
- Recomendações.
- Geração de conteúdos.

### Comunicação

- Telegram Bot API

---

## 5. Estrutura do Projeto

```
job-intelligence-agent/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── scheduler.py
│
│   ├── crawler/
│   │   ├── base.py
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   ├── ashby.py
│   │   └── workday.py
│
│   ├── ai/
│   │   ├── analyzer.py
│   │   ├── scorer.py
│   │   ├── prompts.py
│   │   ├── context_builder.py
│   │   └── resume_parser.py
│
│   ├── database/
│   │   ├── database.py
│   │   ├── models.py
│   │   └── migrations.py
│
│   ├── notifications/
│   │   └── telegram.py
│
│   └── services/
│       ├── jobs_service.py
│       └── users_service.py
│
├── data/
│   ├── database.sqlite
│   └── resumes/
│
├── docs/
│   ├── architecture.md
│   ├── database.md
│   └── roadmap.md
│
├── tests/
│
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## 6. Conceito Multiusuário

O sistema deve ser desenvolvido pensando em múltiplos usuários.

Cada usuário possuirá:

- Conta própria.
- Currículo próprio.
- Perfil profissional.
- Preferências de busca.
- Histórico de aplicações.

Exemplo:

```
Usuário
  |
  +-- Perfil profissional
  |
  +-- Currículo estruturado
  |
  +-- Preferências
  |
  +-- Histórico
```

---

## 7. Modelo de Usuário

**Tabela:** `users`

Campos:

- `id`
- `name`
- `email`
- `telegram_chat_id`
- `created_at`

---

## 8. Perfil Profissional

**Tabela:** `profiles`

Campos:

- `id`
- `user_id`
- `headline`
- `summary`
- `years_experience`
- `desired_roles`
- `desired_locations`
- `languages`
- `salary_expectation`
- `remote_preference`

---

## 9. Currículo Estruturado

O currículo não deve ser utilizado somente como PDF. Ele deve ser transformado em dados estruturados.

**Arquivo:** `candidate_profile.json`

Modelo:

```json
{
  "name": "",
  "summary": "",
  "skills": [],
  "experience": [],
  "education": [],
  "languages": []
}
```

---

## 10. Modelo de Vagas

**Tabela:** `jobs`

Campos:

- `id`
- `title`
- `company`
- `location`
- `country`
- `remote`
- `salary`
- `description`
- `requirements`
- `url`
- `source`
- `created_at`

---

## 11. Crawler Engine

Todos os crawlers devem seguir o mesmo padrão.

Interface:

```python
class BaseCrawler:
    def search_jobs(self):
        pass

    def parse_job(self):
        pass
```

### Primeiros conectores

**Prioridade alta:**
- Greenhouse
- Lever

**Prioridade média:**
- Ashby
- Workday

---

## 12. Inteligência Artificial

A IA será responsável por analisar:

**Entrada:**
- Perfil profissional
- Descrição da vaga

**Saída:**
- Score de compatibilidade
- Pontos positivos
- Pontos negativos
- Recomendação final

---

## 13. Modelo de Score

### Critérios

| Critério     | Peso |
|--------------|------|
| Experiência  | 30%  |
| Localização  | 20%  |
| Idioma       | 15%  |
| Salário      | 15%  |
| Tecnologias  | 10%  |
| Senioridade  | 10%  |

### Resultado

| Faixa   | Classificação          |
|---------|------------------------|
| 0–50    | Baixa compatibilidade  |
| 50–80   | Analisar               |
| 80–100  | Recomendada            |

---

## 14. Telegram Bot

Responsável pelas notificações.

Exemplo de mensagem:

```
🚀 Nova oportunidade encontrada

Empresa: Spotify
Cargo: Product Manager
Local: Suécia

Compatibilidade: 94%

Motivos:
✔ Experiência compatível
✔ Inglês necessário
✔ Produto digital

Link: URL
```

---

## 15. Segurança

**Nunca armazenar:**
- Senhas.
- Tokens.
- Chaves diretamente no código.

**Utilizar:** `.env`

Exemplo:

```
CLAUDE_API_KEY=
TELEGRAM_TOKEN=
DATABASE_URL=
```

---

## 16. Roadmap

### Fase 1 — MVP

**Objetivo:** Criar agente funcional.

Implementar:
- Estrutura Python.
- SQLite.
- Primeiro crawler.
- Telegram.
- Cadastro inicial de perfil.

### Fase 2 — Inteligência Artificial

Implementar:
- Claude API.
- Score automático.
- Ranking.
- Explicação das recomendações.

### Fase 3 — Multiusuário

Implementar:
- Cadastro.
- Login.
- Perfis individuais.
- Currículos.

### Fase 4 — Plataforma SaaS

Implementar:
- Dashboard web.
- Histórico.
- Métricas.
- Gestão de candidaturas.

---

## 17. Princípios de Desenvolvimento

O projeto deve seguir:

- Código modular.
- Baixo acoplamento.
- Fácil manutenção.
- Testes automatizados.
- Documentação contínua.
- Novos conectores devem ser adicionados sem alterar o núcleo do sistema.

---

## 18. Prompt Inicial para Claude Code

```
Você é um engenheiro de software sênior especialista em Python, automação, IA
e arquitetura SaaS.

Vamos desenvolver o Job Intelligence Agent.

Leia toda documentação do projeto antes de iniciar.

Antes de criar código:
1. Analise a arquitetura.
2. Sugira melhorias.
3. Crie o plano de implementação.
4. Configure ambiente Python.
5. Crie estrutura inicial.
6. Gere README.md.
7. Faça implementação incremental.
8. Teste cada etapa antes de avançar.

Priorize qualidade, escalabilidade e organização.
```
