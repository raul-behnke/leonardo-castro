from __future__ import annotations

from zoi_agent.agent.responder import parse_bubbles


def test_simple_split() -> None:
    assert parse_bubbles("oi|||tudo bem|||me conta") == ["oi", "tudo bem", "me conta"]


def test_strip_whitespace() -> None:
    assert parse_bubbles("  oi  |||\n tudo bem\n") == ["oi", "tudo bem"]


def test_drop_empties() -> None:
    assert parse_bubbles("oi||| |||tudo") == ["oi", "tudo"]


def test_max_3_default() -> None:
    out = parse_bubbles("a|||b|||c|||d|||e")
    assert out == ["a", "b", "c"]


def test_max_custom() -> None:
    assert parse_bubbles("a|||b|||c", max_bubbles=2) == ["a", "b"]


def test_empty_input() -> None:
    assert parse_bubbles("") == []
    assert parse_bubbles("   |||  ") == []


def test_single_bubble() -> None:
    assert parse_bubbles("Bora marcar?") == ["Bora marcar?"]
