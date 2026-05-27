from __future__ import annotations

import json
from pathlib import Path

import pytest

from zoi_agent.tools.inventory import (
    InventoryFilters,
    apply_filters,
    norm,
    summarize,
)

FIX = Path(__file__).parent / "fixtures" / "stock_mini.json"


@pytest.fixture
def stock() -> list[dict]:
    return json.loads(FIX.read_text())["vehicles"]


def test_norm() -> None:
    assert norm("Mecânico") == "mecanico"
    assert norm(None) == ""


def test_filter_suv_auto_ate_80mil_zero_exatos(stock: list[dict]) -> None:
    # C6: "SUV automático até 80 mil" → fixture não tem match (Duster passa 80k, Compass tb)
    f = InventoryFilters(carroceria=["SUV"], cambio="Automático", preco_max=80000)
    out = apply_filters(stock, f)
    assert out == []


def test_filter_suv_auto_sem_limite(stock: list[dict]) -> None:
    f = InventoryFilters(carroceria=["SUV"], cambio="Automático")
    ids = [v["external_id"] for v in apply_filters(stock, f)]
    # Duster CVT e Compass Automático
    assert set(ids) == {"1", "4"}
    # Pulse manual fora
    assert "2" not in ids


def test_filter_manual_exclui_cvt(stock: list[dict]) -> None:
    f = InventoryFilters(cambio="Manual")
    ids = [v["external_id"] for v in apply_filters(stock, f)]
    assert "2" in ids
    assert "3" in ids
    assert "1" not in ids
    assert "4" not in ids


def test_filter_preco_min_max(stock: list[dict]) -> None:
    f = InventoryFilters(preco_min=70000, preco_max=100000)
    ids = [v["external_id"] for v in apply_filters(stock, f)]
    assert set(ids) == {"1", "2"}


def test_filter_marca_modelo(stock: list[dict]) -> None:
    f = InventoryFilters(marca=["renault"], modelo=["duster"])
    ids = [v["external_id"] for v in apply_filters(stock, f)]
    assert ids == ["1"]


def test_filter_keywords(stock: list[dict]) -> None:
    f = InventoryFilters(keywords=["sedan"])
    ids = [v["external_id"] for v in apply_filters(stock, f)]
    assert ids == ["3"]


def test_sort_preco_asc(stock: list[dict]) -> None:
    f = InventoryFilters(sort_by="preco_asc")
    out = apply_filters(stock, f)
    precos = [v["preco"] for v in out]
    assert precos == sorted(precos)


def test_opcionais_all_match(stock: list[dict]) -> None:
    f = InventoryFilters(opcionais=["ABS"])
    ids = [v["external_id"] for v in apply_filters(stock, f)]
    assert set(ids) == {"1", "3"}


def test_summarize(stock: list[dict]) -> None:
    s = summarize(stock[0])
    assert s.external_id == "1"
    assert s.imagem == "http://img/1a.jpg"
    assert len(s.opcionais) <= 5
