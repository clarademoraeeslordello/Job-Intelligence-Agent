# Development Guidelines

**Produto:** Job Intelligence Agent

Este documento define as regras que todo código gerado ou revisado (por humanos ou por IA, como Claude Code) deve seguir.

---

## Sempre

- Escrever código limpo e legível (nomes claros, funções pequenas, responsabilidade única).
- Criar testes automatizados para toda nova funcionalidade (`tests/`), especialmente:
  - Crawlers (mockando resposta HTML/Playwright).
  - `scorer.py` (validação de resposta da IA).
  - Deduplicação de vagas.
- Documentar funções e módulos (docstrings claras, explicando entrada/saída).
- Evitar código duplicado — extrair lógica repetida para `services/` ou utilitários compartilhados.
- Usar type hints em todo código Python novo.
- Usar variáveis de ambiente (`.env`) para toda configuração sensível ou dependente de ambiente.
- Seguir o padrão `BaseCrawler` / `JobDTO` para qualquer novo conector (ver `crawler-strategy.md`).
- Seguir o contrato de saída da IA (score + recommendation + reason) definido em `ai-engine.md`.
- Registrar logs relevantes (execução de crawler, chamadas à IA, envio de notificações) para permitir debug.
- Validar dados antes de persistir no banco (evitar vaga sem `url`, sem `source`, etc.).

## Nunca

- Colocar API key, token ou senha diretamente no código — sempre via `.env`.
- Criar arquivos ou módulos sem necessidade real (evitar over-engineering prematuro).
- Quebrar a arquitetura existente (ex: um crawler não deve acessar o banco diretamente — deve passar pelo Job Normalizer).
- Implementar candidatura automática (auto-apply) sem confirmação explícita do usuário (ver `product-requirements.md`, seção "Fora do MVP").
- Notificar o usuário duas vezes pela mesma vaga.
- Sobrescrever uma `job_analysis` existente — nova análise deve gerar novo registro, preservando histórico.
- Fazer scraping agressivo (múltiplas requisições paralelas sem controle) contra a mesma fonte.

---

## Fluxo de Trabalho Recomendado (para Claude Code)

1. Ler toda a documentação em `docs/` antes de iniciar qualquer implementação.
2. Não implementar nada antes de apresentar um plano.
3. Analisar a arquitetura proposta e sugerir melhorias, se houver.
4. Propor o plano de implementação (ex: qual Sprint do roadmap será atacado).
5. Configurar o ambiente Python.
6. Criar a estrutura inicial de pastas/arquivos.
7. Gerar/atualizar o `README.md`.
8. Implementar de forma incremental, testando cada etapa antes de avançar para a próxima.

---

## Convenções de Código

- Python 3.13.
- Formatação: `black` (ou equivalente) para consistência.
- Nomes de arquivo em `snake_case`, classes em `PascalCase`, funções/variáveis em `snake_case`.
- Toda entidade de banco de dados deve ter um model SQLAlchemy correspondente em `app/database/models.py`.
- Toda integração externa (Claude API, Telegram, Playwright) deve ser isolada em seu próprio módulo, nunca chamada diretamente de dentro de `services/` sem uma camada de abstração.

---

## Definition of Done (DoD)

Uma funcionalidade só é considerada concluída quando:

- [ ] O código segue as regras acima.
- [ ] Existem testes cobrindo o caminho feliz e ao menos um caso de erro.
- [ ] A documentação relevante (`docs/`) foi atualizada, se a funcionalidade alterar comportamento descrito nela.
- [ ] Não há segredos (chaves, tokens) commitados no repositório.
- [ ] A funcionalidade foi testada manualmente ao menos uma vez em ambiente local antes de ser considerada pronta.
