"""Calcul du score d'une action à partir des indicateurs définis."""
from __future__ import annotations

from typing import Any

import streamlit as st

from src.data.market import get_history, get_info
from src.screener.indicators import INDICATORS, Indicator


@st.cache_data(ttl=3600, show_spinner=False)
def score_ticker(ticker: str) -> dict[str, Any]:
    """Évalue un ticker selon tous les indicateurs disponibles.

    Renvoie le dict :
        {
          "ticker": str,
          "name": str,
          "global_score": float | None,  # moyenne des notes disponibles
          "n_available": int,
          "indicators": {key: {"value": float|None, "score": int|None,
                                "label": str, "category": str, "fmt": str}},
          "category_scores": {category: float | None},
        }
    """
    info = get_info(ticker)
    history = get_history(ticker, period="1y")

    name = info.get("shortName") or info.get("longName") or ticker

    results: dict[str, dict[str, Any]] = {}
    notes: list[int] = []
    by_cat: dict[str, list[int]] = {}

    for ind in INDICATORS:
        value = _safe(ind.extract, info, history)
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
    }


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception:
        return None


def score_universe(tickers: list[str], progress_cb=None) -> list[dict[str, Any]]:
    """Score tous les tickers, trié par score global décroissant."""
    results = []
    total = len(tickers)
    for i, t in enumerate(tickers, 1):
        try:
            results.append(score_ticker(t))
        except Exception:
            pass
        if progress_cb:
            progress_cb(i / total, t)
    results.sort(
        key=lambda r: (r["global_score"] is not None, r["global_score"] or 0),
        reverse=True,
    )
    return results
