"""Encaminhamento pra vendedor humano.

PLAN §5/§10/§12:
  1) remove tag `agente-ia` do contato (interrompe webhooks futuros)
  2) cria nota com motivo (template completo §10 fica em S13)
  3) dispara workflow GHL_HANDOFF_WORKFLOW_ID (b759fd01-...)
  4) marca sessão terminal_reason (caller faz)

Tolerante a falhas parciais: cada passo é tentado isoladamente; se a tag falhar,
o restante ainda roda. Retorna dict com status por etapa pro log/observabilidade.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from zoi_agent.config import settings
from zoi_agent.ghl import contacts as gc
from zoi_agent.ghl import workflows as gw
from zoi_agent.logging import get_logger
from zoi_agent.metrics import HANDOFF_TOTAL

log = get_logger(__name__)


def _now_sp() -> str:
    return datetime.now(ZoneInfo(settings.app_timezone)).strftime("%Y-%m-%d %H:%M:%S")


def _short_note(motivo: str, terminal_reason: str | None) -> str:
    ts = _now_sp()
    reason = terminal_reason or "handoff"
    return f"[ZOI] {reason} — {ts}\n\nMotivo: {motivo}"


async def encaminhar_para_vendedor(
    *,
    contact_id: str,
    motivo: str,
    terminal_reason: str | None = None,
) -> dict[str, bool]:
    """Executa as 3 ações em paralelo lógico (mas sequencial pra logging). Retorna
    {"tag_removed": bool, "note_created": bool, "workflow_added": bool}.
    O caller deve gravar terminal_reason no state."""
    result = {"tag_removed": False, "note_created": False, "workflow_added": False}
    tag = settings.ghl_tag_agent_gate
    workflow_id = settings.ghl_handoff_workflow_id

    try:
        await gc.remove_tag(contact_id, [tag])
        result["tag_removed"] = True
    except Exception as e:
        log.error("handoff_remove_tag_failed", contact_id=contact_id, err=str(e))

    try:
        await gc.add_note(contact_id, _short_note(motivo, terminal_reason))
        result["note_created"] = True
    except Exception as e:
        log.error("handoff_note_failed", contact_id=contact_id, err=str(e))

    try:
        await gw.add_to_workflow(contact_id, workflow_id)
        result["workflow_added"] = True
    except Exception as e:
        log.error("handoff_workflow_failed", contact_id=contact_id, err=str(e))

    HANDOFF_TOTAL.labels(reason=terminal_reason or "unknown").inc()
    log.info(
        "handoff_done",
        contact_id=contact_id,
        terminal_reason=terminal_reason,
        motivo=motivo[:80],
        **result,
    )
    return result
