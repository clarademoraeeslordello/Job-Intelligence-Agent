# AI Engine

**Produto:** Job Intelligence Agent
**Motor de IA:** Claude API

---

## 1. Papel da IA no Sistema

A IA é o diferencial do produto. Ela não serve apenas para "ler a descrição da vaga" — ela é responsável por conectar o **contexto do usuário** (currículo, experiência, objetivos, preferências) com cada oportunidade encontrada, e traduzir isso em uma recomendação acionável.

Responsabilidades:

- Análise de compatibilidade entre perfil e vaga.
- Ranking de vagas.
- Geração de explicações (pontos positivos/negativos).
- Geração de conteúdos auxiliares (futuramente: rascunho de carta de apresentação, ajuste de currículo por vaga, etc.).

---

## 2. User Context Engine

Antes de qualquer chamada à IA, o sistema monta um **contexto do usuário**, que combina:

- Currículo estruturado (`resumes.structured_json`): skills, experiências, formação, idiomas.
- Perfil profissional (`profiles`): cargos desejados, localização desejada, expectativa salarial, preferência de modelo de trabalho.
- Histórico (futuramente): vagas que o usuário aplicou, ignorou, ou marcou como irrelevante — usado para refinar recomendações ao longo do tempo.

Esse contexto é montado por um módulo dedicado (`app/context/` ou `app/ai/context_builder.py`), e não deve ficar implícito dentro do prompt do analyzer. Isso permite:

- Reutilizar o mesmo motor de IA para múltiplos usuários com perfis diferentes.
- Evoluir o contexto (ex: aprendizado a partir do histórico) sem alterar a lógica de análise da vaga em si.
- Auditar exatamente qual contexto foi usado em cada análise (armazenado em `job_analysis.raw_ai_response`).

```
Resume + Profile + (Histórico futuro)
              |
              v
     User Context Engine
              |
              v
      Contexto consolidado
              |
              v
        AI Analyzer (Claude)
```

---

## 3. Análise de Vaga

### Entrada

```
Contexto do usuário (currículo + perfil + preferências)
+
Descrição da vaga (título, empresa, localização, requisitos, descrição completa)
```

### Saída (formato estruturado)

```json
{
  "score": 95,
  "recommendation": "APPLY",
  "reason": {
    "positive": [
      "Experiência compatível com a senioridade exigida",
      "Idioma exigido (inglês) já dominado pelo candidato",
      "Localização compatível com preferência de remoto"
    ],
    "negative": [
      "Faixa salarial não informada"
    ]
  }
}
```

Regras:
- `score`: número de 0 a 100.
- `recommendation`: enum `APPLY` (80–100), `ANALYZE` (50–80), `IGNORE` (0–50) — consistente com o `Modelo de Score` definido em `architecture.md`.
- `reason`: sempre deve conter ao menos um ponto positivo e, quando existir, os pontos de atenção. Nunca retornar apenas o score sem justificativa (ver regra de produto em `product-requirements.md`).

---

## 4. Critérios de Score (referência)

Os mesmos pesos definidos em `architecture.md`:

| Critério     | Peso |
|--------------|------|
| Experiência  | 30%  |
| Localização  | 20%  |
| Idioma       | 15%  |
| Salário      | 15%  |
| Tecnologias  | 10%  |
| Senioridade  | 10%  |

A IA deve considerar esses pesos como guia, mas tem liberdade para ajustar a nota final quando identificar fatores qualitativos relevantes (ex: descrição da vaga menciona explicitamente um requisito eliminatório que o candidato não atende).

---

## 5. Estrutura de Prompt (alto nível)

Arquivo: `app/ai/prompts.py`

```
System:
Você é um analista de recrutamento especialista em compatibilidade
candidato-vaga. Sempre responda apenas em JSON, no formato especificado.

User:
### Contexto do candidato
{contexto_consolidado}

### Vaga
Título: {title}
Empresa: {company}
Local: {location}
Descrição: {description}
Requisitos: {requirements}

### Tarefa
Avalie a compatibilidade seguindo os critérios: Experiência (30%),
Localização (20%), Idioma (15%), Salário (15%), Tecnologias (10%),
Senioridade (10%).

Responda apenas em JSON no formato:
{"score": int, "recommendation": "APPLY"|"ANALYZE"|"IGNORE",
 "reason": {"positive": [...], "negative": [...]}}
```

---

## 6. Componentes (`app/ai/`)

- `context_builder.py` — monta o contexto consolidado do usuário (User Context Engine).
- `prompts.py` — templates de prompt.
- `analyzer.py` — orquestra a chamada à Claude API (contexto + vaga → resposta).
- `scorer.py` — valida/normaliza a resposta da IA (garante que o JSON está no formato esperado, aplica fallback caso a IA retorne algo inesperado).
- `resume_parser.py` — transforma currículo (PDF/texto) em `candidate_profile.json` estruturado.

---

## 7. Tratamento de Falhas

- Se a resposta da IA não vier em JSON válido, `scorer.py` deve tentar uma reparsagem simples (remover blocos de markdown, etc.) antes de falhar.
- Se a análise falhar definitivamente, a vaga deve ser marcada para nova tentativa posterior, e **não** deve gerar notificação (evitar notificar com score inválido/zerado).
- Todas as respostas brutas da IA devem ser armazenadas (`job_analysis.raw_ai_response`) para auditoria e para permitir reprocessamento caso o prompt seja melhorado no futuro.

---

## 8. Evolução Futura

- Aprendizado a partir do feedback do usuário (aplicou / ignorou / marcou como irrelevante) para recalibrar o peso dos critérios por usuário.
- Geração assistida de materiais de candidatura (carta de apresentação, ajuste de resumo do currículo para a vaga específica).
- Comparação entre vagas similares para ajudar o usuário a priorizar quando há múltiplas boas opções na mesma semana.
