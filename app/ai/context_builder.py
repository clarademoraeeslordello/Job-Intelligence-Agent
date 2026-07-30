from dataclasses import dataclass, field

from app.database.models import User


@dataclass
class UserContext:
    """Contexto consolidado do usuario (User Context Engine — ver docs/ai-engine.md secao 2)."""

    headline: str | None
    summary: str | None
    years_experience: int | None
    desired_roles: list[str]
    desired_locations: list[str]
    languages: list[str]
    salary_expectation: str | None
    remote_preference: str | None
    resume: dict = field(default_factory=dict)

    def as_prompt_text(self) -> str:
        lines = [
            f"Cargo desejado: {', '.join(self.desired_roles) or 'nao informado'}",
            f"Localizacao desejada: {', '.join(self.desired_locations) or 'nao informado'}",
            f"Idiomas: {', '.join(self.languages) or 'nao informado'}",
            f"Anos de experiencia: {self.years_experience if self.years_experience is not None else 'nao informado'}",
            f"Expectativa salarial: {self.salary_expectation or 'nao informado'}",
            f"Preferencia de modelo de trabalho: {self.remote_preference or 'nao informado'}",
        ]
        if self.summary:
            lines.append(f"Resumo profissional: {self.summary}")
        if self.resume.get("skills"):
            lines.append(f"Skills: {', '.join(self.resume['skills'])}")
        if self.resume.get("experience"):
            lines.append(f"Experiencia: {self.resume['experience']}")
        return "\n".join(lines)


def build_user_context(user: User) -> UserContext:
    """Monta o contexto consolidado a partir de Profile + Resume (ver ai-engine.md).

    Nao inclui aprendizado a partir de historico de interacao (aplicou/ignorou) ainda —
    fica para Fase 2 do roadmap.md, nao faz parte do escopo desta Fase 4.
    """
    profile = user.profile
    resume = user.resume

    return UserContext(
        headline=profile.headline if profile else None,
        summary=profile.summary if profile else None,
        years_experience=profile.years_experience if profile else None,
        desired_roles=profile.desired_roles if profile else [],
        desired_locations=profile.desired_locations if profile else [],
        languages=profile.languages if profile else [],
        salary_expectation=profile.salary_expectation if profile else None,
        remote_preference=profile.remote_preference if profile else None,
        resume=resume.structured_json if resume else {},
    )
