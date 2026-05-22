"""Calculs de valorisation et P&L pour le portefeuille."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.data.market import get_fx_rate, get_quote


@dataclass
class EnrichedPosition:
    ticker: str
    name: str
    quantity: float
    purchase_price: float
    purchase_date: str
    currency: str
    price: float | None
    cost: float
    value: float | None
    pnl: float | None
    pnl_pct: float | None
    value_eur: float | None
    pnl_eur: float | None


def enrich_position(pos: dict[str, Any]) -> EnrichedPosition:
    quote = get_quote(pos["ticker"])
    price = quote["price"] if quote and quote.get("price") else None
    currency = quote["currency"] if quote else "EUR"
    name = quote["name"] if quote else pos["ticker"]

    quantity = float(pos["quantity"])
    purchase_price = float(pos["purchase_price"])
    cost = quantity * purchase_price
    value = quantity * price if price is not None else None
    pnl = (value - cost) if value is not None else None
    pnl_pct = (pnl / cost * 100) if pnl is not None and cost else None

    fx = get_fx_rate(currency, "EUR") if currency != "EUR" else 1.0
    value_eur = (value * fx) if (value is not None and fx is not None) else None
    pnl_eur = (pnl * fx) if (pnl is not None and fx is not None) else None

    return EnrichedPosition(
        ticker=pos["ticker"],
        name=name,
        quantity=quantity,
        purchase_price=purchase_price,
        purchase_date=pos.get("purchase_date", ""),
        currency=currency,
        price=price,
        cost=cost,
        value=value,
        pnl=pnl,
        pnl_pct=pnl_pct,
        value_eur=value_eur,
        pnl_eur=pnl_eur,
    )


def aggregate(enriched: list[EnrichedPosition]) -> dict[str, float | None]:
    """Totaux du portefeuille en EUR."""
    total_value = sum(p.value_eur for p in enriched if p.value_eur is not None)
    total_cost_eur = 0.0
    for p in enriched:
        fx = get_fx_rate(p.currency, "EUR") if p.currency != "EUR" else 1.0
        if fx is None:
            continue
        total_cost_eur += p.cost * fx
    total_pnl = total_value - total_cost_eur if total_cost_eur else None
    total_pnl_pct = (total_pnl / total_cost_eur * 100) if total_pnl is not None and total_cost_eur else None
    return {
        "value": total_value,
        "cost": total_cost_eur,
        "pnl": total_pnl,
        "pnl_pct": total_pnl_pct,
        "n_positions": len(enriched),
    }
