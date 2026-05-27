"""Smoke C6: 'tem SUV automático até 80mil?' ao vivo (GHL + OpenAI)."""
from __future__ import annotations

import asyncio
import json
import sys

from zoi_agent.ghl.client import close_client
from zoi_agent.logging import configure_logging, get_logger
from zoi_agent.tools.inventory import (
    extract_filters,
    get_vehicle_details,
    load_inventory,
    search_inventory,
)


async def main(query: str) -> int:
    configure_logging()
    log = get_logger("smoke_inv")

    inv = await load_inventory()
    log.info("inv_loaded", total=len(inv))

    print(f"\n=== query ===\n{query}\n")

    filters = await extract_filters(query)
    print(f"=== filtros extraídos ===")
    print(json.dumps(filters.model_dump(exclude_none=True), indent=2, ensure_ascii=False))

    result = await search_inventory(query)
    print(f"\n=== resultado ===")
    print(f"exatos: {len(result.exatos)} | parecidos: {len(result.parecidos)} | total: {result.total}")

    for v in result.exatos[:5]:
        print(f"  [EX] {v.titulo} ({v.ano}) — R$ {v.preco:.0f} — {v.cambio} — {v.external_id}")
    for p in result.parecidos[:5]:
        v = p["vehicle"]
        print(f"  [SIM] {v['titulo']} ({v['ano']}) — R$ {v['preco']:.0f} — {v['cambio']}")
        print(f"        motivo: {p['motivo']}")

    if result.exatos:
        det = await get_vehicle_details(result.exatos[0].external_id)
        print(f"\n=== get_vehicle_details({result.exatos[0].external_id}) ===")
        print(f"keys: {sorted(det.keys()) if det else None}")

    await close_client()
    return 0


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "tem SUV automático até 80 mil?"
    sys.exit(asyncio.run(main(query)))
