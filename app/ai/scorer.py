import json
import re
from dataclasses import dataclass

VALID_RECOMMENDATIONS = {"APPLY", "ANALYZE", "IGNORE"}


class InvalidAIResponseError(Exception):
    """A resposta da IA nao pode ser interpretada como uma analise valida."""


@dataclass
class JobScore:
    score: float
    recommendation: str
    positive_points: list[str]
    negative_points: list[str]
    raw_response: dict


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_ai_response(raw_text: str) -> JobScore:
    """Valida/normaliza a resposta da IA (ver ai-engine.md secao 3 e 7).

    Tenta uma reparsagem simples (remover blocos de markdown) antes de falhar.
    Nunca retorna um score sem justificativa: reason.positive e obrigatorio.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            data = json.loads(_strip_markdown_fences(raw_text))
        except json.JSONDecodeError as exc:
            raise InvalidAIResponseError(f"resposta nao e JSON valido: {raw_text!r}") from exc

    try:
        score = float(data["score"])
        recommendation = data["recommendation"]
        reason = data["reason"]
        positive = list(reason["positive"])
        negative = list(reason.get("negative", []))
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidAIResponseError(f"resposta em formato inesperado: {data!r}") from exc

    if recommendation not in VALID_RECOMMENDATIONS:
        raise InvalidAIResponseError(f"recommendation invalida: {recommendation!r}")
    if not 0 <= score <= 100:
        raise InvalidAIResponseError(f"score fora do intervalo 0-100: {score!r}")
    if not positive:
        raise InvalidAIResponseError("resposta sem nenhum ponto positivo (reason.positive vazio)")

    return JobScore(
        score=score,
        recommendation=recommendation,
        positive_points=positive,
        negative_points=negative,
        raw_response=data,
    )
