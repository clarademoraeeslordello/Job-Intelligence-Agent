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
        f"{RESPONSE_FORMAT_INSTRUCTIONS}"
    )
