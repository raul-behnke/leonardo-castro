from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from zoi_agent.config import settings
from zoi_agent.tools import handoff as h


@pytest.fixture
def patches(monkeypatch):
    remove_mock = AsyncMock()
    note_mock = AsyncMock()
    wf_mock = AsyncMock()
    monkeypatch.setattr(h.gc, "remove_tag", remove_mock)
    monkeypatch.setattr(h.gc, "add_note", note_mock)
    monkeypatch.setattr(h.gw, "add_to_workflow", wf_mock)
    return {"remove": remove_mock, "note": note_mock, "wf": wf_mock}


@pytest.mark.asyncio
async def test_handoff_full_success(patches) -> None:
    res = await h.encaminhar_para_vendedor(
        contact_id="c1", motivo="lead pediu", terminal_reason="handoff_solicitado"
    )
    assert res == {"tag_removed": True, "note_created": True, "workflow_added": True}
    patches["remove"].assert_awaited_once_with("c1", [settings.ghl_tag_agent_gate])
    note_arg = patches["note"].await_args.args[1]
    assert "handoff_solicitado" in note_arg
    assert "lead pediu" in note_arg
    patches["wf"].assert_awaited_once_with("c1", settings.ghl_handoff_workflow_id)


@pytest.mark.asyncio
async def test_handoff_partial_failure_tag(patches) -> None:
    patches["remove"].side_effect = RuntimeError("403")
    res = await h.encaminhar_para_vendedor(
        contact_id="c1", motivo="x", terminal_reason="handoff_solicitado"
    )
    assert res["tag_removed"] is False
    assert res["note_created"] is True
    assert res["workflow_added"] is True


@pytest.mark.asyncio
async def test_handoff_partial_failure_workflow(patches) -> None:
    patches["wf"].side_effect = RuntimeError("workflow gone")
    res = await h.encaminhar_para_vendedor(
        contact_id="c1", motivo="x", terminal_reason="handoff_erro"
    )
    assert res["tag_removed"] is True
    assert res["note_created"] is True
    assert res["workflow_added"] is False
