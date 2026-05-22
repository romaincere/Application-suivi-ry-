"""Calcul du score d'une action à partir des indicateurs définis."""
from __future__ import annotations

from typing import Any

import streamlit as st

from src.data.ai_ratings import get_ai_ratings, is_configured as ai_ready
from src.data.finnhub import insider_transactions, is_configured as finnhub_ready
from src.data.market import (
    get_balance_sheet,
    get_cashflow,
    get_dividends,
    get_financials,
    get_history,
    get_info,
)
from src.screener.indicators import INDICATORS
from src.storage.ratings_store import load_ratings


@st.cache_data(ttl=3600, show_spinner=False)
def score_ticker(ticker: str, use_ai: bool = False) -> dict[str, Any]:
    """Évalue un ticker selon tous les indicateurs disponibles.

    Si `use_ai=True` et qu'une clé Anthropic est configurée, complète
    Moat / Qualité management / Parts de marché par une estimation IA
    (uniquement pour les critères non déjà notés manuellement).
    """
    info = get_info(ticker)
    name = info.get("shortName") or info.get("longName") or ticker

    manual = load_ratings()
    ai_ratings = None
    if use_ai and ai_ready():
        ai_ratings = get_ai_ratings(ticker, name, info)

    ctx = {
        "ticker": ticker.upper(),
        "info": info,
        "history": get_history(ticker, period="1y"),
        "financials": get_financials(ticker),
        "balance_sheet": get_balance_sheet(ticker),
        "cashflow": get_cashflow(ticker),
        "dividends": get_dividends(ticker),
        "insider": insider_transactions(ticker) if finnhub_ready() else None,
        "manual": manual,
        "ai_ratings": ai_ratings,
    }

    results: dict[str, dict[str, Any]] = {}
    notes: list[int] = []
    by_cat: dict[str, list[int]] = {}

    for ind in INDICATORS:
        value = _safe(ind.extract, ctx)
        score = ind.score(value)
        results[ind.key] = {
            "value": value,
            "score": score,
            "label": ind.label,
            "category": ind.category,
            "fmt": ind.fmt,
        }
        if score is not None:
            notes.append(score)
            by_cat.setdefault(ind.category, []).append(score)

    global_score = sum(notes) / len(notes) if notes else None
    cat_scores = {c: (sum(s) / len(s) if s else None) for c, s in by_cat.items()}

    return {
        "ticker": ticker,
        "name": name,
        "global_score": global_score,
        "n_available": len(notes),
        "indicators": results,
        "category_scores": cat_scores,
        "ai_ratings": ai_ratings,
    }


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception:
        return None


def score_universe(
    tickers: list[str], progress_cb=None, use_ai: bool = False
) -> list[dict[str, Any]]:
    """Score tous les tickers, trié par score global décroissant."""
    results = []
    total = len(tickers)
    for i, t in enumerate(tickers, 1):
        try:
            results.append(score_ticker(t, use_ai=use_ai))
        except Exception:
            pass
        if progress_cb:
            progress_cb(i / total, t)
    results.sort(
        key=lambda r: (r["global_score"] is not None, r["global_score"] or 0),
        reverse=True,
    )
    return results
