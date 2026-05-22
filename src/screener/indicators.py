"""Définition des indicateurs fondamentaux + techniques et de leur scoring.

Chaque indicateur produit une note ∈ {0, 50, 100} d'après les seuils du
tableau Excel ; les valeurs manquantes sont ignorées dans la note globale.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

# ────────────────────────── scoring helpers ──────────────────────────


def _higher_better(excellent: float, neutral: float):
    def score(v: float | None) -> int | None:
        if v is None:
            return None
        if v >= excellent:
            return 100
        if v >= neutral:
            return 50
        return 0
    return score


def _lower_better(excellent: float, neutral: float):
    def score(v: float | None) -> int | None:
        if v is None:
            return None
        if v <= excellent:
            return 100
        if v <= neutral:
            return 50
        return 0
    return score


def _band(excellent: tuple[float, float], neutral: tuple[float, float]):
    """Excellent si ∈ [e_lo, e_hi], neutre si ∈ [n_lo, n_hi], mauvais sinon."""
    def score(v: float | None) -> int | None:
        if v is None:
            return None
        if excellent[0] <= v <= excellent[1]:
            return 100
        if neutral[0] <= v <= neutral[1]:
            return 50
        return 0
    return score


# ────────────────────────── extractors ──────────────────────────


def _from_info(field: str, scale: float = 1.0):
    def extract(info: dict, _hist: pd.DataFrame) -> float | None:
        v = info.get(field)
        if v is None:
            return None
        try:
            return float(v) * scale
        except (TypeError, ValueError):
            return None
    return extract


def _ma_signal(_info: dict, hist: pd.DataFrame) -> float | None:
    """Ratio MM50/MM200 : >1 → 50j au-dessus de 200j (haussier)."""
    if hist is None or len(hist) < 200:
        return None
    close = hist["Close"]
    ma50 = close.tail(50).mean()
    ma200 = close.tail(200).mean()
    if not ma200:
        return None
    return ma50 / ma200


def _rsi14(_info: dict, hist: pd.DataFrame) -> float | None:
    if hist is None or len(hist) < 15:
        return None
    delta = hist["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if pd.notna(val) else None


def _perf_1y(_info: dict, hist: pd.DataFrame) -> float | None:
    if hist is None or len(hist) < 200:
        return None
    first = hist["Close"].iloc[0]
    last = hist["Close"].iloc[-1]
    if not first:
        return None
    return (last / first - 1) * 100


# ────────────────────────── indicators ──────────────────────────


@dataclass
class Indicator:
    key: str
    label: str
    category: str
    extract: Callable[[dict, pd.DataFrame], float | None]
    score: Callable[[float | None], int | None]
    fmt: str = "{:.2f}"


# Indicateurs en % stockés en décimal dans yfinance → on passe en % pour le scoring.
INDICATORS: list[Indicator] = [
    # ── Croissance ─────────────────────────────────────────────
    Indicator(
        "revenue_growth", "Croissance CA", "Croissance",
        _from_info("revenueGrowth", scale=100),
        _higher_better(15, 5),
        fmt="{:+.1f} %",
    ),
    Indicator(
        "eps_growth", "Croissance EPS", "Croissance",
        _from_info("earningsGrowth", scale=100),
        _higher_better(20, 5),
        fmt="{:+.1f} %",
    ),
    # ── Rentabilité ────────────────────────────────────────────
    Indicator(
        "roe", "ROE", "Rentabilité",
        _from_info("returnOnEquity", scale=100),
        _higher_better(15, 8),
        fmt="{:.1f} %",
    ),
    Indicator(
        "net_margin", "Marge nette", "Rentabilité",
        _from_info("profitMargins", scale=100),
        _higher_better(15, 5),
        fmt="{:.1f} %",
    ),
    # ── Valorisation ───────────────────────────────────────────
    Indicator(
        "pe", "PER", "Valorisation",
        _from_info("trailingPE"),
        _band(excellent=(10, 25), neutral=(5, 40)),
    ),
    Indicator(
        "peg", "PEG", "Valorisation",
        _from_info("pegRatio"),
        _lower_better(excellent=1.5, neutral=2.5),
    ),
    Indicator(
        "ps", "Price to Sales", "Valorisation",
        _from_info("priceToSalesTrailing12Months"),
        _lower_better(excellent=5, neutral=10),
    ),
    # ── Solidité ───────────────────────────────────────────────
    # debtToEquity dans yfinance est en pourcentage (50 → ratio 0.5).
    Indicator(
        "debt_equity", "Debt / Equity", "Solidité",
        _from_info("debtToEquity", scale=0.01),
        _lower_better(excellent=1, neutral=2),
    ),
    Indicator(
        "current_ratio", "Current Ratio", "Solidité",
        _from_info("currentRatio"),
        _higher_better(excellent=1.5, neutral=1),
    ),
    # ── Momentum ───────────────────────────────────────────────
    Indicator(
        "ma_signal", "MM50 / MM200", "Momentum",
        _ma_signal,
        _band(excellent=(1.0, 99), neutral=(0.98, 1.0)),
        fmt="{:.3f}",
    ),
    Indicator(
        "rsi", "RSI 14", "Momentum",
        _rsi14,
        _band(excellent=(40, 65), neutral=(30, 70)),
        fmt="{:.0f}",
    ),
    Indicator(
        "perf_1y", "Performance 1A", "Momentum",
        _perf_1y,
        _higher_better(excellent=20, neutral=0),
        fmt="{:+.1f} %",
    ),
]

CATEGORIES = ["Croissance", "Rentabilité", "Valorisation", "Solidité", "Momentum"]
