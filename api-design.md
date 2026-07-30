# API Design

**Produto:** Job Intelligence Agent
**Status:** Placeholder — a ser detalhado na Fase 4 (Plataforma SaaS)

---

## 1. Contexto

No MVP (Fase 1) e nas Fases 2 e 3, o sistema não expõe uma API pública — a interação com o usuário acontece via Telegram, e a lógica interna é acessada apenas pelos módulos do próprio `app/`.

Este documento será detalhado quando o projeto evoluir para uma plataforma SaaS com dashboard web (Fase 4, ver `roadmap.md`), momento em que será necessário expor endpoints para:

- Autenticação de usuários (login/cadastro).
- CRUD de perfil e currículo.
- Consulta de vagas e análises (`jobs`, `job_analysis`).
- Gestão de candidaturas (`applications`).
- Configuração de preferências de notificação.

---

## 2. Decisões a tomar futuramente

- Framework: FastAPI é o candidato natural (tipagem, performance, integração fácil com SQLAlchemy/Pydantic).
- Autenticação: JWT vs. sessão — a definir conforme necessidade do dashboard.
- Versionamento: `/api/v1/...` desde o início para permitir evolução sem quebrar clientes.
- Rate limiting e autenticação de terceiros (caso a API seja aberta a integrações externas no futuro).

---

## 3. Próximos passos

Este documento deve ser reescrito com endpoints, contratos de request/response e regras de autenticação assim que a Fase 4 do roadmap for iniciada. Até lá, ele serve apenas como lembrete de que a API pública **não faz parte do escopo do MVP**.
