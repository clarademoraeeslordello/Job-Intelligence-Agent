import pytest

from app.ai.scorer import InvalidAIResponseError, parse_ai_response

VALID_JSON = (
    '{"score": 95, "recommendation": "APPLY", '
    '"reason": {"positive": ["experiencia compativel"], "negative": []}}'
)


def test_parse_valid_response():
    result = parse_ai_response(VALID_JSON)

    assert result.score == 95
    assert result.recommendation == "APPLY"
    assert result.positive_points == ["experiencia compativel"]


def test_parse_response_wrapped_in_markdown_fence():
    wrapped = f"```json\n{VALID_JSON}\n```"

    result = parse_ai_response(wrapped)

    assert result.score == 95


def test_parse_response_with_prose_after_markdown_fence():
    # Caso real observado em producao: o Haiku escreve texto explicativo
    # depois do bloco JSON, entao a fenca nao envolve a resposta inteira.
    wrapped = f"```json\n{VALID_JSON}\n```\n\nAnalise adicional: esta vaga parece boa."

    result = parse_ai_response(wrapped)

    assert result.score == 95


def test_parse_response_with_prose_before_and_after_no_fence():
    wrapped = f"Aqui esta minha analise:\n{VALID_JSON}\nEspero que ajude."

    result = parse_ai_response(wrapped)

    assert result.score == 95


def test_parse_invalid_json_raises():
    with pytest.raises(InvalidAIResponseError):
        parse_ai_response("isso nao e json")


def test_parse_response_without_positive_points_raises():
    invalid = '{"score": 80, "recommendation": "APPLY", "reason": {"positive": [], "negative": []}}'

    with pytest.raises(InvalidAIResponseError):
        parse_ai_response(invalid)


def test_parse_response_with_invalid_recommendation_raises():
    invalid = (
        '{"score": 80, "recommendation": "MAYBE", ' '"reason": {"positive": ["x"], "negative": []}}'
    )

    with pytest.raises(InvalidAIResponseError):
        parse_ai_response(invalid)


def test_parse_response_with_score_out_of_range_raises():
    invalid = (
        '{"score": 150, "recommendation": "APPLY", '
        '"reason": {"positive": ["x"], "negative": []}}'
    )

    with pytest.raises(InvalidAIResponseError):
        parse_ai_response(invalid)
