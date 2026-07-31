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


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_fenced_block(text: str) -> str | None:
    """Busca um bloco ```json ... ``` em qualquer posicao do texto (nao so
    quando ele envolve a resposta inteira - o modelo as vezes escreve
    comentario em texto livre depois do bloco JSON)."""
    match = _FENCE_RE.search(text)
    return match.group(1) if match else None


def _extract_first_balanced_object(text: str) -> str | None:
    """Fallback final: extrai o primeiro objeto JSON balanceado (contando
    chaves), ignorando qualquer texto antes/depois - cobre respostas sem
    cercas de markdown mas com prosa antes ou depois do JSON."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i, char in enumerate(text[start:], start=start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def parse_ai_response(raw_text: str) -> JobScore:
    """Valida/normaliza a resposta da IA (ver ai-engine.md secao 3 e 7).

    Tenta reparsagens sucessivas (bloco de markdown em qualquer posicao, depois
    o primeiro objeto JSON balanceado) antes de desistir. Nunca retorna um score
    sem justificativa: reason.positive e obrigatorio.
    """
    candidates = [raw_text]
    fenced = _extract_fenced_block(raw_text)
    if fenced is not None:
        candidates.append(fenced)
    balanced = _extract_first_balanced_object(raw_text)
    if balanced is not None:
        candidates.append(balanced)

    data = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue
    if data is None:
        raise InvalidAIResponseError(f"resposta nao e JSON valido: {raw_text!r}")

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
