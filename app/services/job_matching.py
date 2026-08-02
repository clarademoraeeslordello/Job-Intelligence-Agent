"""Pre-filtro de aderencia, aplicado ANTES de gastar chamada de IA.

Motivacao (run 30696057497, 01/08/2026): as fontes abrangentes (Arbeitnow,
RemoteOK) trazem ~150 vagas novas por dia, majoritariamente engenharia de
software. Com teto de 30 analises por disparo escolhidas apenas por
`created_at desc`, a IA gastava quase todo o orcamento pontuando vagas
irrelevantes (maior score do dia: 45 de 100) enquanto vagas aderentes podiam
nem chegar a ser analisadas.

Este modulo nao decide se a vaga presta - isso continua sendo da IA. Ele so
ordena a fila e descarta o que nao tem nenhuma relacao com os cargos desejados
do usuario, para que as 30 analises pagas sejam gastas nas 30 vagas mais
promissoras em vez das 30 mais recentes.

Os criterios saem do Profile de cada usuario (desired_roles,
remote_preference), nunca de listas fixas no codigo - mesmo principio ja
adotado no prompt de IA (ver app/ai/prompts.py).
"""

import logging
import re
import unicodedata

from sqlalchemy.orm import Session

from app.database.models import Job, JobAnalysis, Profile, User

logger = logging.getLogger(__name__)

TITLE_TOKEN_WEIGHT = 10
TITLE_PHRASE_WEIGHT = 25
DESCRIPTION_TOKEN_WEIGHT = 1
DESCRIPTION_TOKEN_CAP = 5

LANGUAGE_REQUIREMENT_MARKERS: dict[str, tuple[str, ...]] = {
    "german": ("m/w/d", "w/m/d", "deutschkenntnisse", "deutsch in wort", "fliessend deutsch"),
    "french": ("francais courant", "maitrise du francais", "langue francaise"),
    "dutch": ("vloeiend nederlands", "nederlands sprekend"),
    "italian": ("italiano fluente", "conoscenza dell italiano"),
    "spanish": ("espanol nativo", "castellano nativo"),
}
# Corte grosso de idioma, antes da IA. So marcadores inequivocos de que o anuncio
# EXIGE a lingua - o julgamento fino (nivel exigido vs nivel do candidato) continua
# sendo da IA, que ja recebe Profile.languages.
#
# Cuidado deliberado com "(m/f/d)": e a variante inglesa do marcador de genero
# alemao e aparece em anuncio alemao escrito EM INGLES, que serve. So "(m/w/d)" e
# "(w/m/d)" indicam anuncio em alemao. Confundir os dois derrubaria metade das
# vagas boas medidas em dry-run.

LANGUAGE_ALIASES: dict[str, tuple[str, ...]] = {
    "german": ("german", "alemao", "deutsch"),
    "french": ("french", "frances", "francais"),
    "dutch": ("dutch", "holandes", "nederlands"),
    "italian": ("italian", "italiano"),
    "spanish": ("spanish", "espanhol", "espanol", "castellano"),
}
# Profile.languages e texto livre ("Ingles avancado", "English", "en"), entao o
# casamento e por alias em vez de igualdade exata.

MIN_TITLE_TOKENS = 2
# Um unico token generico do cargo no titulo nao qualifica a vaga. Medido em
# dry-run contra 357 vagas reais (02/08/2026): so com "manager", "analyst",
# "business" ou "data" sobreviviam coisas como "Tequila Market Manager",
# "Senior Supply Chain Manager" e "Senior Information Security Analyst" - 115
# sobreviventes para um teto de 30 analises, metade delas lixo. Exigindo frase
# exata do cargo ou dois tokens ("Product" + "Manager"), a triagem passa a
# entregar so vaga da area.

_STOPWORDS = frozenset(
    {
        "and",
        "the",
        "for",
        "with",
        "que",
        "com",
        "dos",
        "das",
        "por",
        "para",
        "sobre",
        "senior",
        "junior",
        "pleno",
        "staff",
        "lead",
        "principal",
        "sr",
        "jr",
    }
)
# Removidos por serem ruido: aparecem em quase todo titulo de vaga e nao
# discriminam area (um "Senior Backend Engineer" casaria com "Senior Product
# Manager" so pelo "senior").


def _normalize(text: str | None) -> str:
    """Minusculas sem acento, para casar 'Gerente de Produto' com 'gerente de produto'."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _tokens(text: str | None) -> set[str]:
    """Palavras significativas (>= 3 letras, sem stopwords) de um texto."""
    return {
        token
        for token in re.split(r"[^a-z0-9]+", _normalize(text))
        if len(token) >= 3 and token not in _STOPWORDS
    }


def speaks(profile: Profile, language: str) -> bool:
    """Se o usuario declarou a lingua em Profile.languages (comparacao por alias)."""
    declared = " ".join(_normalize(entry) for entry in (profile.languages or []))
    return any(alias in declared for alias in LANGUAGE_ALIASES.get(language, (language,)))


def requires_unavailable_language(job: Job, profile: Profile) -> str | None:
    """Lingua que o anuncio exige e que o usuario nao declarou, se houver.

    Sem Profile.languages preenchido nao ha o que comparar - nao descarta nada,
    para nao zerar a fila por perfil incompleto.
    """
    if not profile.languages:
        return None

    haystack = f"{_normalize(job.title)} {_normalize(job.description)}"
    for language, markers in LANGUAGE_REQUIREMENT_MARKERS.items():
        if speaks(profile, language):
            continue
        if any(marker in haystack for marker in markers):
            return language
    return None


def is_eligible(job: Job, profile: Profile) -> tuple[bool, str]:
    """Cortes eliminatorios, aplicados antes de qualquer pontuacao.

    Diferente do ranking, aqui nao ha meio-termo: reprovar em remoto ou em idioma
    tira a vaga da fila, por melhor que fosse a aderencia de cargo. Retorna
    tambem o motivo, para o log dizer por que a fila encolheu.
    """
    # Deliberadamente so o flag `remote` da fonte, nunca inferido da localizacao
    # (decisao da Clara, 02/08/2026): "Berlin, Remote" costuma ser hibrido
    # presencial, e o custo do falso positivo e ela receber vaga que nao serve.
    if profile.remote_preference == "remote" and not job.remote:
        return False, "nao_remota"

    language = requires_unavailable_language(job, profile)
    if language:
        return False, f"exige_{language}"

    return True, "elegivel"


def relevance_score(job: Job, profile: Profile | None) -> int:
    """Pontua o quanto a vaga se parece com o que o usuario procura (0 = nenhuma relacao).

    Nao e o score de compatibilidade - esse continua vindo da IA (0-100). Aqui
    e so um ranking barato de triagem.

    A qualificacao e decidida pelo TITULO: ou o titulo contem a frase exata de
    um cargo desejado, ou contem pelo menos MIN_TITLE_TOKENS tokens desse
    cargo. A descricao so desempata entre vagas ja qualificadas - se bastasse a
    descricao, qualquer vaga que cite "product" no texto entraria na fila paga.
    """
    if profile is None or not profile.desired_roles:
        return 0

    role_tokens: set[str] = set()
    score = 0
    qualified = False
    normalized_title = _normalize(job.title)
    title_tokens = _tokens(job.title)

    for role in profile.desired_roles:
        tokens_of_role = _tokens(role)
        role_tokens |= tokens_of_role
        normalized_role = _normalize(role)
        if normalized_role and normalized_role in normalized_title:
            score += TITLE_PHRASE_WEIGHT
            qualified = True
        elif len(tokens_of_role & title_tokens) >= MIN_TITLE_TOKENS:
            qualified = True

    if not qualified:
        return 0

    score += TITLE_TOKEN_WEIGHT * len(role_tokens & title_tokens)

    description_hits = len(role_tokens & _tokens(job.description))
    score += DESCRIPTION_TOKEN_WEIGHT * min(description_hits, DESCRIPTION_TOKEN_CAP)

    return score


def select_jobs_for_user(session: Session, user: User, limit: int) -> list[Job]:
    """Vagas que valem a analise paga para este usuario, das mais aderentes para as menos.

    Considera apenas vagas ainda nao analisadas para o usuario - antes, o corte
    pegava as N mais recentes globalmente e depois descartava as ja analisadas,
    o que fazia um disparo render zero analises sempre que as N mais recentes
    ja tinham sido vistas, mesmo havendo vagas antigas na fila.

    Sem desired_roles no perfil nao ha como triar: cai no comportamento
    anterior (mais recentes primeiro), sem descartar nada.
    """
    analyzed_job_ids = {
        job_id
        for (job_id,) in session.query(JobAnalysis.job_id).filter(JobAnalysis.user_id == user.id)
    }
    pending = [job for job in session.query(Job).all() if job.id not in analyzed_job_ids]

    profile = user.profile
    if profile is None or not profile.desired_roles:
        logger.warning(
            "user_id=%s sem desired_roles no perfil - triagem por aderencia desativada, "
            "usando as vagas mais recentes",
            user.id,
        )
        ranked = sorted(pending, key=lambda job: job.created_at, reverse=True)
        return ranked[:limit]

    rejections: dict[str, int] = {}
    eligible = []
    for job in pending:
        ok, reason = is_eligible(job, profile)
        if ok:
            eligible.append(job)
        else:
            rejections[reason] = rejections.get(reason, 0) + 1

    scored = [(relevance_score(job, profile), job) for job in eligible]
    relevant = [(score, job) for score, job in scored if score > 0]
    relevant.sort(key=lambda pair: (pair[0], pair[1].created_at), reverse=True)
    selected = [job for _, job in relevant[:limit]]

    rejections["fora_do_perfil"] = len(eligible) - len(relevant)
    logger.info(
        "triagem user_id=%s pendentes=%s selecionadas=%s descartes=%s",
        user.id,
        len(pending),
        len(selected),
        ", ".join(f"{reason}={count}" for reason, count in sorted(rejections.items()) if count),
    )
    return selected
