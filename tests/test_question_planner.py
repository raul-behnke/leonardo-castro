from __future__ import annotations

from zoi_agent.agent.question_planner import (
    CANONICAL_QUESTIONS,
    compute_missing,
    plan_next_question,
    push_asked_field,
)
from zoi_agent.agent.schemas import (
    Collected,
    SessionState,
    StateUpdate,
    TrocaInfo,
)


def _upd(**kw) -> StateUpdate:
    base = dict(
        stage="descoberta",
        collected=Collected(),
        missing=[],
        next_action="x",
        sentiment="neutro",
        intent="qualificar",
    )
    base.update(kw)
    return StateUpdate(**base)


def test_missing_vazio_quando_tudo_preenchido() -> None:
    c = Collected(
        nome="Raul", veiculo_interesse="Duster", veiculo_interesse_confirmado=True,
        intencao="compra_direta", possui_troca=False,
        motivo_compra_ou_troca="trabalho", forma_pagamento="financiado",
        cidade="Taubaté", interesse_agendamento=True,
    )
    assert compute_missing(c) == []


def test_missing_subcampos_troca() -> None:
    c = Collected(possui_troca=True, troca_completa=TrocaInfo(modelo="Gol", ano=2013))
    miss = compute_missing(c)
    assert "troca_completa.modelo" not in miss   # preenchido
    assert "troca_completa.ano" not in miss      # preenchido
    assert "troca_completa.km" in miss
    assert "troca_completa.quitado" in miss


def test_missing_pula_troca_quando_sem_troca() -> None:
    """possui_troca=False -> subcampos não aparecem em missing."""
    c = Collected(intencao="compra_direta", possui_troca=False)
    miss = compute_missing(c)
    assert not any(f.startswith("troca_completa.") for f in miss)


def test_plan_proximo_missing() -> None:
    state = SessionState(collected=Collected(nome="Raul"))
    nq = plan_next_question(state=state, update=_upd())
    assert nq.field == "veiculo_interesse"
    assert nq.intent == "funil"
    assert "veículo" in nq.canonical_text.lower()


def test_plan_pula_campo_perguntado_duas_vezes() -> None:
    """Se um campo foi perguntado 2x sem resposta, pula pro próximo."""
    state = SessionState(
        collected=Collected(nome="Raul"),
        last_asked_fields=["veiculo_interesse", "veiculo_interesse"],
    )
    nq = plan_next_question(state=state, update=_upd())
    # veiculo_interesse foi pedido 2x ainda sem resposta -> pula pro próximo
    assert nq.field != "veiculo_interesse"
    assert nq.field in (
        "veiculo_interesse_confirmado", "intencao", "possui_troca",
    )


def test_plan_terminal_sem_pergunta() -> None:
    state = SessionState(terminal_reason="qualificado_agendado")
    nq = plan_next_question(state=state, update=_upd())
    assert nq.field is None
    assert nq.intent == "nenhum"


def test_plan_duvida_suspende_funil() -> None:
    state = SessionState(collected=Collected(nome="Raul"))
    nq = plan_next_question(state=state, update=_upd(intent_secundario="duvida_operacional"))
    assert nq.intent == "duvida"
    assert nq.skip_funnel_reason is not None


def test_plan_apresentacao_eh_pergunta_de_foco() -> None:
    state = SessionState(collected=Collected())
    nq = plan_next_question(state=state, update=_upd(intent="apresentar"))
    assert nq.intent == "foco"


def test_plan_agendamento_quando_gate_atendido() -> None:
    state = SessionState(collected=Collected(
        veiculo_interesse_confirmado=True,
        interesse_agendamento=True,
    ))
    nq = plan_next_question(state=state, update=_upd())
    assert nq.intent == "agendamento"


def test_push_asked_field_rolling_window() -> None:
    state = SessionState()
    for f in ["a", "b", "c", "d", "e", "f"]:
        push_asked_field(state, f, window=5)
    # mantém últimas 5
    assert state.last_asked_fields == ["b", "c", "d", "e", "f"]


def test_plan_comprar_pula_troca() -> None:
    """C concreto: lead disse compra_direta + possui_troca=False -> planner
    pula direto pra motivo (subcampos de troca filtrados, motivo é próximo)."""
    state = SessionState(collected=Collected(
        nome="Raul",
        veiculo_interesse="Duster",
        veiculo_interesse_confirmado=True,
        intencao="compra_direta",
        possui_troca=False,
    ))
    nq = plan_next_question(state=state, update=_upd())
    assert nq.field == "motivo_compra_ou_troca"


def test_canonical_questions_completo() -> None:
    """Toda chave de PRIORITY_FUNNEL deve ter frase canônica."""
    from zoi_agent.agent.question_planner import PRIORITY_FUNNEL

    for f in PRIORITY_FUNNEL:
        assert f in CANONICAL_QUESTIONS, f"falta canonical pra {f}"
