from app.ai.context_builder import UserContext
from app.database.models import Job

SYSTEM_PROMPT = (
    "Voce e um analista de recrutamento especialista em compatibilidade "
    "candidato-vaga. Sempre responda apenas em JSON, no formato especificado."
)

RESPONSE_FORMAT_INSTRUCTIONS = (
    'Responda apenas em JSON no formato: {"score": int, '
    '"recommendation": "APPLY"|"ANALYZE"|"IGNORE", '
    '"reason": {"positive": [...], "negative": [...]}}'
)


def build_user_message(context: UserContext, job: Job) -> str:
    """Monta o prompt de usuario combinando contexto consolidado + vaga (ver ai-engine.md secao 5)."""
    return (
        "### Contexto do candidato\n"
        f"{context.as_prompt_text()}\n\n"
        "### Vaga\n"
        f"Titulo: {job.title}\n"
        f"Empresa: {job.company}\n"
        f"Local: {job.location or 'nao informado'}\n"
        f"Descricao: {job.description}\n"
        f"Requisitos: {job.requirements or 'nao informado'}\n\n"
        "### Tarefa\n"
        "Avalie a compatibilidade seguindo os criterios: Experiencia (30%), "
        "Localizacao (20%), Idioma (15%), Salario (15%), Tecnologias (10%), "
        "Senioridade (10%).\n\n"
        "Criterios eliminatorios (se a vaga violar qualquer um destes, "
        "recommendation deve ser IGNORE independente do score calculado acima):\n"
        "- A vaga exige nivel de ingles avancado/fluente/nativo quando o candidato tem "
        "apenas nivel intermediario, E a vaga deixa isso explicito como requisito "
        "obrigatorio (nao apenas desejavel).\n"
        "- A vaga e remota mas restrita a candidatos de um pais/regiao/nacionalidade/"
        "autorizacao de trabalho especifica que o candidato nao atende (ex: 'US-based "
        "only', 'EU work authorization required', exige visto que o candidato nao possui) "
        "- considerando a nacionalidade, localizacao e situacao de elegibilidade do "
        "candidato descritas no contexto acima, se houver.\n"
        "- A vaga exige um tipo de contratacao (CLT/full-time employment, PJ/contractor, "
        "cooperativa) diferente de todos os tipos aceitos pelo candidato, E isso esta "
        "explicito na vaga (a maioria das vagas nao especifica isso - so aplique esta "
        "regra se a vaga for explicita).\n\n"
        f"{RESPONSE_FORMAT_INSTRUCTIONS}"
    )
