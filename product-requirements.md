# Product Requirements Document (PRD)

**Produto:** Job Intelligence Agent
**Versão:** 1.0

---

## 1. Produto

Job Intelligence Agent é um agente de IA que atua como um recrutador pessoal: busca vagas, entende o perfil do candidato e recomenda apenas oportunidades que realmente fazem sentido.

O diferencial do produto **não é encontrar vagas** — isso já existe em dezenas de sites (LinkedIn, Indeed, Glassdoor, etc.). O diferencial é o **contexto**: o sistema conhece o currículo, a experiência, os objetivos e as preferências do usuário, e usa isso para filtrar o ruído.

> "Eu conheço seu currículo, sua experiência, seus objetivos e sei quais vagas fazem sentido para você."

Esse contexto é o que torna o produto útil desde o primeiro usuário (uso pessoal/familiar) até a versão multiusuário (SaaS).

---

## 2. Usuários

### Fase inicial (uso pessoal)
- Você (owner do projeto).
- Familiares próximos (ex: esposa, mãe).

### Fase futura (SaaS)
- Profissionais em transição de carreira.
- Pessoas buscando emprego que não têm tempo de vasculhar dezenas de sites por dia.
- Recrutadores/headhunters (possível expansão B2B, fora do escopo inicial).

---

## 3. Problema

Buscar vagas compatíveis manualmente exige muito tempo:

- Vagas estão espalhadas em múltiplas plataformas (Greenhouse, Lever, Ashby, Workday, LinkedIn, etc.).
- A maioria das vagas listadas não é compatível com o perfil do candidato.
- Avaliar manualmente requisitos, senioridade, idioma, localização e salário para cada vaga é repetitivo e cansativo.
- Sem um filtro inteligente, o candidato perde tempo ou perde oportunidades boas por não ter visto a vaga a tempo.

---

## 4. Solução

Um agente de IA que:

- Busca vagas automaticamente em múltiplas fontes (ATS crawlers).
- Entende o perfil profissional e o currículo estruturado do usuário (**User Context Engine**).
- Analisa cada vaga encontrada frente a esse contexto.
- Gera um score de compatibilidade e uma recomendação (aplicar, analisar, ignorar).
- Notifica o usuário via Telegram apenas com o que importa.

### User Context Engine (conceito central)

Camada responsável por manter e evoluir o **entendimento do usuário** ao longo do tempo:

- Currículo estruturado (skills, experiências, formação, idiomas).
- Preferências explícitas (localização, remoto, salário, cargos desejados).
- Aprendizado implícito (vagas que o usuário gostou, ignorou ou aplicou).

Essa camada é o que diferencia o produto de um simples agregador de vagas, e é o que permite reutilizar o mesmo sistema para múltiplas pessoas com perfis completamente diferentes (você, sua esposa, sua mãe), cada uma com seu próprio contexto.

> Nota de arquitetura: recomenda-se incluir esse conceito como um módulo explícito (`app/context/`) desde o MVP, mesmo que simples no início, para evitar que a lógica de "entendimento do usuário" fique espalhada dentro do `ai/analyzer.py`.

---

## 5. MVP

O sistema deve, no mínimo:

- [ ] Cadastrar usuário.
- [ ] Cadastrar currículo estruturado (JSON).
- [ ] Cadastrar perfil profissional e preferências de busca.
- [ ] Buscar vagas automaticamente (pelo menos 1 fonte: Greenhouse).
- [ ] Analisar vagas com IA (Claude API) usando o contexto do usuário.
- [ ] Gerar score de compatibilidade.
- [ ] Enviar alertas via Telegram para vagas relevantes (score acima de um limite configurável).

### Critério de sucesso do MVP

O usuário recebe, sem esforço manual, notificações de vagas que ele mesmo consideraria relevantes ao navegar manualmente — com uma taxa de "falso positivo" (vaga irrelevante notificada) baixa o suficiente para não gerar fadiga de notificação.

---

## 6. Fora do MVP

Não implementar nas fases iniciais:

- Candidatura automática (auto-apply).
- Scraping agressivo ou em larga escala (respeitar rate limits e termos de uso das fontes).
- Pagamentos / cobrança.
- Dashboard web complexo.
- Login social / múltiplos métodos de autenticação.
- Múltiplos idiomas de interface.

Esses itens fazem parte das fases 2, 3 e 4 do roadmap (ver `roadmap.md`).

---

## 7. Regras de Produto

- O sistema nunca deve enviar notificação duplicada para a mesma vaga.
- O sistema nunca deve aplicar automaticamente em nome do usuário sem confirmação explícita.
- Toda vaga armazenada deve ter rastreabilidade da fonte (`source`) e da URL original.
- O score de compatibilidade deve sempre vir acompanhado de uma justificativa (pontos positivos/negativos), nunca apenas um número.
- Preferências do usuário podem mudar ao longo do tempo; o sistema deve permitir atualização do perfil sem precisar recriar o cadastro.

---

## 8. Métricas de Sucesso (futuras)

Ainda que fora do escopo do MVP, vale já ter em mente para orientar decisões técnicas:

- Número de vagas relevantes notificadas por semana.
- Taxa de vagas marcadas como "relevante" pelo usuário / total notificado.
- Tempo entre publicação da vaga e notificação ao usuário.
- Número de candidaturas geradas a partir de recomendações do agente.
