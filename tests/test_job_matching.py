from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.models import Base, Job, JobAnalysis, Profile, User
from app.services.job_matching import is_eligible, relevance_score, select_jobs_for_user

ROLES = ["Product Manager", "Product Owner", "Gerente de Produto"]


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_user(session, roles=ROLES, remote_preference="any", languages=None) -> User:
    user = User(name="Clara", email="clara@example.com", telegram_chat_id="1")
    session.add(user)
    session.flush()
    session.add(
        Profile(
            user_id=user.id,
            desired_roles=list(roles),
            remote_preference=remote_preference,
            languages=list(languages) if languages is not None else [],
            notification_score_threshold=75.0,
        )
    )
    session.commit()
    return user


def _make_job(
    session, title, external_id=None, description="desc", remote=True, created_at=None
) -> Job:
    external_id = external_id or title
    job = Job(
        title=title,
        company="acme",
        location="Berlin",
        # nao "Remote": is_eligible tambem le a localizacao, entao um default
        # remoto mascararia o corte de vaga presencial nos testes
        country=None,
        remote=remote,
        salary=None,
        description=description,
        requirements=None,
        url=f"https://x.com/{external_id}",
        source="arbeitnow",
        external_id=external_id,
        created_at=created_at or datetime.now(timezone.utc),
    )
    session.add(job)
    session.commit()
    return job


def _profile(session, user) -> Profile:
    return user.profile


# --- relevance_score ---------------------------------------------------------


def test_matching_title_scores_higher_than_unrelated_title(session):
    user = _make_user(session)
    match = _make_job(session, "Product Manager", external_id="a")
    unrelated = _make_job(session, "Senior Backend Engineer", external_id="b")

    assert relevance_score(match, _profile(session, user)) > relevance_score(
        unrelated, _profile(session, user)
    )


def test_unrelated_title_and_description_scores_zero(session):
    user = _make_user(session)
    job = _make_job(session, "Senior Backend Engineer", description="Kubernetes, Go, gRPC")

    assert relevance_score(job, _profile(session, user)) == 0


def test_accents_are_ignored_when_matching(session):
    user = _make_user(session)
    job = _make_job(session, "Gerente de Produto Sênior")

    assert relevance_score(job, _profile(session, user)) > 0


def test_seniority_words_alone_do_not_create_relevance(session):
    """'Senior' e stopword: um Senior Backend Engineer nao pode casar com
    Senior Product Manager so pela senioridade."""
    user = _make_user(session, roles=["Senior Product Manager"])
    job = _make_job(session, "Senior Backend Engineer", description="Go, Kubernetes")

    assert relevance_score(job, _profile(session, user)) == 0


def test_exact_role_phrase_in_title_outranks_scattered_token_match(session):
    user = _make_user(session)
    exact = _make_job(session, "Product Manager", external_id="a")
    loose = _make_job(session, "Owner of Product, Payments", external_id="b")

    assert relevance_score(exact, _profile(session, user)) > relevance_score(
        loose, _profile(session, user)
    )


def test_non_remote_job_is_ineligible_when_user_wants_remote(session):
    user = _make_user(session, remote_preference="remote")
    onsite = _make_job(session, "Product Manager", external_id="b", remote=False)

    assert is_eligible(onsite, _profile(session, user)) == (False, "nao_remota")


def test_non_remote_job_is_eligible_when_user_accepts_any(session):
    user = _make_user(session, remote_preference="any")
    onsite = _make_job(session, "Product Manager", remote=False)

    assert is_eligible(onsite, _profile(session, user))[0] is True


def test_remote_in_location_does_not_make_an_onsite_job_eligible(session):
    """So o flag `remote` da fonte vale. 'Berlin, Remote' costuma ser hibrido
    presencial - decisao da Clara em 02/08/2026, apos ver o trade-off."""
    user = _make_user(session, remote_preference="remote")
    job = _make_job(session, "Product Manager", remote=False)
    job.location = "Remote-United Kingdom"
    session.commit()

    assert is_eligible(job, _profile(session, user)) == (False, "nao_remota")


def test_job_requiring_undeclared_language_is_ineligible(session):
    user = _make_user(session, languages=["Portugues", "Ingles"])
    job = _make_job(
        session,
        "Product Manager (m/w/d)",
        description="Sehr gute Deutschkenntnisse in Wort und Schrift.",
    )

    assert is_eligible(job, _profile(session, user)) == (False, "exige_german")


def test_job_requiring_a_declared_language_stays_eligible(session):
    """Quem fala alemao nao pode perder vaga alema."""
    user = _make_user(session, languages=["Portugues", "Ingles", "Alemao"])
    job = _make_job(session, "Product Manager (m/w/d)", description="Deutschkenntnisse.")

    assert is_eligible(job, _profile(session, user))[0] is True


def test_portuguese_and_english_jobs_are_never_cut_by_language(session):
    user = _make_user(session, languages=["Portugues", "Ingles"])
    for description in (
        "Fluent English required. Remote-first team.",
        "Vaga para atuacao remota, exige portugues fluente.",
    ):
        job = _make_job(
            session, "Product Manager", external_id=description[:20], description=description
        )
        assert is_eligible(job, _profile(session, user))[0] is True, description


def test_english_gender_marker_does_not_count_as_german_requirement(session):
    """'(m/f/d)' e a variante inglesa do marcador alemao e aparece em anuncio
    escrito em ingles - so '(m/w/d)' indica anuncio em alemao."""
    user = _make_user(session, languages=["Portugues", "Ingles"])
    job = _make_job(
        session,
        "Senior Product Manager - Operations (m/f/d)",
        description="We are looking for a product manager. English is our working language.",
    )

    assert is_eligible(job, _profile(session, user))[0] is True


def test_language_cut_is_disabled_when_profile_declares_no_languages(session):
    """Perfil incompleto nao pode zerar a fila."""
    user = _make_user(session, languages=[])
    job = _make_job(session, "Product Manager (m/w/d)", description="Deutschkenntnisse.")

    assert is_eligible(job, _profile(session, user))[0] is True


def test_select_drops_non_remote_and_wrong_language_jobs(session):
    user = _make_user(session, languages=["Portugues", "Ingles"], remote_preference="remote")
    keeper = _make_job(session, "Product Manager", external_id="ok", remote=True)
    _make_job(session, "Product Owner", external_id="onsite", remote=False)
    _make_job(
        session,
        "Product Manager (m/w/d)",
        external_id="de",
        remote=True,
        description="Deutschkenntnisse erforderlich.",
    )

    selected = select_jobs_for_user(session, user, limit=30)

    assert [job.id for job in selected] == [keeper.id]


def test_single_generic_token_in_title_does_not_qualify(session):
    """Regressao medida em dry-run com 357 vagas reais: so 'manager' ou 'analyst'
    no titulo fazia sobreviver vaga de outra area inteira."""
    user = _make_user(session)
    for title in (
        "Tequila Market Manager New York",
        "Senior Supply Chain Manager",
        "Senior Information Security Analyst",
        "Regional Sales Manager",
    ):
        job = _make_job(session, title, description="nada a ver com produto")
        assert relevance_score(job, _profile(session, user)) == 0, title


def test_two_role_tokens_in_title_qualify_without_exact_phrase(session):
    """'Product Owner' nao aparece literalmente, mas os dois tokens do cargo sim."""
    user = _make_user(session, roles=["Product Owner"])
    job = _make_job(session, "Owner of Product, Payments")

    assert relevance_score(job, _profile(session, user)) > 0


def test_single_word_role_qualifies_by_exact_phrase(session):
    """Cargo de uma palavra so nunca alcancaria MIN_TITLE_TOKENS - tem que passar
    pelo casamento de frase."""
    user = _make_user(session, roles=["Produtora"])
    job = _make_job(session, "Produtora de Conteudo")

    assert relevance_score(job, _profile(session, user)) > 0


def test_description_alone_does_not_qualify_an_unrelated_title(session):
    """Se a descricao bastasse, qualquer vaga que cite 'product' no texto entraria
    na fila paga."""
    user = _make_user(session)
    job = _make_job(
        session,
        "Senior Backend Engineer",
        description="You will work closely with our product manager and product owner.",
    )

    assert relevance_score(job, _profile(session, user)) == 0


def test_profile_without_desired_roles_scores_zero(session):
    user = _make_user(session, roles=[])
    job = _make_job(session, "Product Manager")

    assert relevance_score(job, _profile(session, user)) == 0


def test_relevance_score_without_profile_is_zero(session):
    job = _make_job(session, "Product Manager")

    assert relevance_score(job, None) == 0


# --- select_jobs_for_user ----------------------------------------------------


def test_select_discards_jobs_without_any_relevance(session):
    user = _make_user(session)
    relevant = _make_job(session, "Product Owner", external_id="a")
    _make_job(session, "Senior Backend Engineer", external_id="b", description="Go, Kubernetes")
    _make_job(session, "DevOps Specialist", external_id="c", description="Terraform, AWS")

    selected = select_jobs_for_user(session, user, limit=30)

    assert [job.id for job in selected] == [relevant.id]


def test_select_orders_by_relevance_not_recency(session):
    user = _make_user(session)
    now = datetime.now(timezone.utc)
    weak = _make_job(
        session, "Owner of Product, Payments", external_id="weak", created_at=now
    )  # mais recente, qualifica por tokens mas sem frase exata
    strong = _make_job(
        session,
        "Product Manager",
        external_id="strong",
        created_at=now - timedelta(hours=10),
    )  # mais antiga, aderencia forte

    selected = select_jobs_for_user(session, user, limit=30)

    assert [job.id for job in selected] == [strong.id, weak.id]


def test_select_respects_limit(session):
    user = _make_user(session)
    for i in range(10):
        _make_job(session, f"Product Manager {i}", external_id=str(i))

    selected = select_jobs_for_user(session, user, limit=4)

    assert len(selected) == 4


def test_select_skips_jobs_already_analyzed_for_the_user(session):
    user = _make_user(session)
    analyzed = _make_job(session, "Product Manager", external_id="a")
    pending = _make_job(session, "Product Owner", external_id="b")
    session.add(
        JobAnalysis(job_id=analyzed.id, user_id=user.id, score=90.0, recommendation="APPLY")
    )
    session.commit()

    selected = select_jobs_for_user(session, user, limit=30)

    assert [job.id for job in selected] == [pending.id]


def test_select_reaches_older_pending_jobs_when_recent_ones_are_analyzed(session):
    """Regressao: o corte antigo pegava as N mais recentes globalmente e so depois
    descartava as ja analisadas, fazendo o disparo render zero analises mesmo
    havendo vagas aderentes na fila."""
    user = _make_user(session)
    now = datetime.now(timezone.utc)
    old_pending = _make_job(
        session, "Product Manager", external_id="old", created_at=now - timedelta(days=2)
    )
    for i in range(5):
        recent = _make_job(
            session,
            f"Product Owner {i}",
            external_id=f"recent{i}",
            created_at=now - timedelta(minutes=i),
        )
        session.add(
            JobAnalysis(job_id=recent.id, user_id=user.id, score=10.0, recommendation="IGNORE")
        )
    session.commit()

    selected = select_jobs_for_user(session, user, limit=3)

    assert [job.id for job in selected] == [old_pending.id]


def test_select_falls_back_to_recency_when_profile_has_no_desired_roles(session):
    """Sem desired_roles nao ha como triar - nao pode descartar tudo e ficar sem
    analisar nada."""
    user = _make_user(session, roles=[])
    now = datetime.now(timezone.utc)
    older = _make_job(session, "Product Manager", external_id="a", created_at=now - timedelta(1))
    newer = _make_job(session, "Backend Engineer", external_id="b", created_at=now)

    selected = select_jobs_for_user(session, user, limit=30)

    assert [job.id for job in selected] == [newer.id, older.id]
