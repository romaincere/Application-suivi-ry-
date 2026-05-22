"""Définition des indicateurs fondamentaux + techniques et de leur scoring.

Chaque indicateur produit une note ∈ {0, 50, 100} d'après les seuils du
tableau Excel ; les valeurs manquantes sont ignorées dans la note globale.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

Context = dict[str, Any]  # {info, history, financials, balance_sheet, cashflow, insider, manual, ticker}


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
    def score(v: float | None) -> int | None:
        if v is None:
            return None
        if excellent[0] <= v <= excellent[1]:
            return 100
        if neutral[0] <= v <= neutral[1]:
            return 50
        return 0
    return score


def _passthrough(v: float | None) -> int | None:
    """Pour les indicateurs où l'extractor renvoie directement 0/50/100."""
    if v is None:
        return None
    return int(v)


# ────────────────────────── financials helpers ──────────────────────────


def _find_row(df: pd.DataFrame, *aliases: str) -> pd.Series | None:
    if df is None or df.empty:
        return None
    for name in aliases:
        if name in df.index:
            return df.loc[name]
    return None


# ────────────────────────── extractors ──────────────────────────


def _from_info(field: str, scale: float = 1.0):
    def extract(ctx: Context) -> float | None:
        v = ctx["info"].get(field)
        if v is None:
            return None
        try:
            return float(v) * scale
        except (TypeError, ValueError):
            return None
    return extract


def _ma_signal(ctx: Context) -> float | None:
    hist = ctx.get("history")
    if hist is None or len(hist) < 200:
        return None
    close = hist["Close"]
    ma50 = close.tail(50).mean()
    ma200 = close.tail(200).mean()
    if not ma200:
        return None
    return ma50 / ma200


def _rsi14(ctx: Context) -> float | None:
    hist = ctx.get("history")
    if hist is None or len(hist) < 15:
        return None
    delta = hist["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if pd.notna(val) else None


def _perf_1y(ctx: Context) -> float | None:
    hist = ctx.get("history")
    if hist is None or len(hist) < 200:
        return None
    first = hist["Close"].iloc[0]
    last = hist["Close"].iloc[-1]
    if not first:
        return None
    return (last / first - 1) * 100


def _cagr_revenue(ctx: Context) -> float | None:
    """CAGR du chiffre d'affaires sur l'historique dispo (4-5 ans)."""
    row = _find_row(ctx.get("financials"), "Total Revenue", "Revenue", "TotalRevenue")
    if row is None:
        return None
    values = row.dropna().sort_index()  # ascending (oldest first)
    if len(values) < 2:
        return None
    first, last = float(values.iloc[0]), float(values.iloc[-1])
    n_years = len(values) - 1
    if first <= 0 or last <= 0 or n_years == 0:
        return None
    return ((last / first) ** (1 / n_years) - 1) * 100


def _roic(ctx: Context) -> float | None:
    """ROIC = NOPAT / (Equity + Total Debt). Taux d'impôt approximé à 25%."""
    fin = ctx.get("financials")
    bs = ctx.get("balance_sheet")
    ebit_row = _find_row(fin, "EBIT", "Operating Income", "OperatingIncome")
    equity_row = _find_row(
        bs, "Stockholders Equity", "Total Stockholder Equity",
        "Common Stock Equity", "StockholdersEquity",
    )
    debt_row = _find_row(bs, "Total Debt", "TotalDebt", "Long Term Debt")
    if ebit_row is None or equity_row is None or debt_row is None:
        return None
    try:
        ebit = float(ebit_row.iloc[0])
        equity = float(equity_row.iloc[0])
        debt = float(debt_row.iloc[0])
    except (IndexError, ValueError, TypeError):
        return None
    capital = equity + debt
    if capital <= 0:
        return None
    return (ebit * 0.75) / capital * 100  # NOPAT après impôt 25%


def _fcf_trend(ctx: Context) -> float | None:
    """Croissance moyenne du FCF. Sentinelle -999 si dernier FCF négatif."""
    row = _find_row(ctx.get("cashflow"), "Free Cash Flow", "FreeCashFlow")
    if row is None:
        return None
    values = row.dropna().sort_index()
    if len(values) < 2:
        return None
    last = float(values.iloc[-1])
    if last < 0:
        return -999.0  # FCF négatif aujourd'hui = signal mauvais
    growths = []
    for i in range(1, len(values)):
        prev = float(values.iloc[i - 1])
        curr = float(values.iloc[i])
        if prev > 0:
            growths.append((curr - prev) / prev * 100)
    if not growths:
        return None
    return sum(growths) / len(growths)


def _fcf_scorer(v: float | None) -> int | None:
    if v is None:
        return None
    if v <= -100:  # sentinelle FCF négatif
        return 0
    if v >= 15:
        return 100
    if v >= 0:
        return 50
    return 0


def _insider_ratio(ctx: Context) -> float | None:
    """Ratio achats/ventes des initiés sur 6 mois ∈ [-1, 1]."""
    insider = ctx.get("insider")
    if not insider:
        return None
    return insider.get("ratio")


def _upside_vs_target(ctx: Context) -> float | None:
    """Décote/prime du cours actuel vs objectif moyen des analystes (%).

    >0 → action sous-évaluée (le marché est en-dessous du juste prix consensus).
    <0 → action surévaluée (le marché a déjà dépassé le juste prix).
    """
    info = ctx["info"]
    target = info.get("targetMeanPrice") or info.get("targetMedianPrice")
    current = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
    )
    if not target or not current:
        return None
    try:
        target_f = float(target)
        current_f = float(current)
    except (TypeError, ValueError):
        return None
    if target_f <= 0 or current_f <= 0:
        return None
    return (target_f - current_f) / current_f * 100


def _manual(key: str):
    def extract(ctx: Context) -> float | None:
        ratings = ctx.get("manual") or {}
        return ratings.get(ctx["ticker"], {}).get(key)
    return extract


# ────────────────────────── indicators ──────────────────────────


@dataclass
class Indicator:
    key: str
    label: str
    category: str
    extract: Callable[[Context], float | None]
    score: Callable[[float | None], int | None]
    fmt: str = "{:.2f}"


INDICATORS: list[Indicator] = [
    # ── Croissance ─────────────────────────────────────────────
    Indicator("revenue_growth", "Croissance CA", "Croissance",
              _from_info("revenueGrowth", scale=100),
              _higher_better(15, 5), fmt="{:+.1f} %"),
    Indicator("eps_growth", "Croissance EPS", "Croissance",
              _from_info("earningsGrowth", scale=100),
              _higher_better(20, 5), fmt="{:+.1f} %"),
    Indicator("cagr_5y", "CAGR CA 5A", "Croissance",
              _cagr_revenue,
              _higher_better(15, 5), fmt="{:+.1f} %"),
    # ── Rentabilité ────────────────────────────────────────────
    Indicator("roe", "ROE", "Rentabilité",
              _from_info("returnOnEquity", scale=100),
              _higher_better(15, 8), fmt="{:.1f} %"),
    Indicator("roic", "ROIC", "Rentabilité",
              _roic,
              _higher_better(12, 6), fmt="{:.1f} %"),
    Indicator("net_margin", "Marge nette", "Rentabilité",
              _from_info("profitMargins", scale=100),
              _higher_better(15, 5), fmt="{:.1f} %"),
    # ── Valorisation ───────────────────────────────────────────
    Indicator("pe", "PER", "Valorisation",
              _from_info("trailingPE"),
              _band(excellent=(10, 25), neutral=(5, 40))),
    Indicator("peg", "PEG", "Valorisation",
              _from_info("pegRatio"),
              _lower_better(excellent=1.5, neutral=2.5)),
    Indicator("ps", "Price to Sales", "Valorisation",
              _from_info("priceToSalesTrailing12Months"),
              _lower_better(excellent=5, neutral=10)),
    Indicator("upside", "Upside vs juste prix", "Valorisation",
              _upside_vs_target,
              _higher_better(excellent=15, neutral=0), fmt="{:+.1f} %"),
    # ── Solidité ───────────────────────────────────────────────
    Indicator("debt_equity", "Debt / Equity", "Solidité",
              _from_info("debtToEquity", scale=0.01),
              _lower_better(excellent=1, neutral=2)),
    Indicator("fcf_trend", "FCF (croissance)", "Solidité",
              _fcf_trend, _fcf_scorer, fmt="{:+.1f} %"),
    Indicator("current_ratio", "Current Ratio", "Solidité",
              _from_info("currentRatio"),
              _higher_better(excellent=1.5, neutral=1)),
    # ── Momentum ───────────────────────────────────────────────
    Indicator("ma_signal", "MM50 / MM200", "Momentum",
              _ma_signal,
              _band(excellent=(1.0, 99), neutral=(0.98, 1.0)), fmt="{:.3f}"),
    Indicator("rsi", "RSI 14", "Momentum",
              _rsi14,
              _band(excellent=(40, 65), neutral=(30, 70)), fmt="{:.0f}"),
    Indicator("perf_1y", "Performance 1A", "Momentum",
              _perf_1y,
              _higher_better(excellent=20, neutral=0), fmt="{:+.1f} %"),
    # ── Qualité ────────────────────────────────────────────────
    Indicator("moat", "Moat (manuel)", "Qualité",
              _manual("moat"), _passthrough, fmt="{:.0f}"),
    Indicator("insider", "Insider Buying", "Qualité",
              _insider_ratio,
              _band(excellent=(0.3, 1.01), neutral=(-0.3, 0.3)), fmt="{:+.2f}"),
    Indicator("market_share", "Parts de marché (manuel)", "Qualité",
              _manual("market_share"), _passthrough, fmt="{:.0f}"),
]

CATEGORIES = ["Croissance", "Rentabilité", "Valorisation", "Solidité", "Momentum", "Qualité"]
MANUAL_KEYS = ["moat", "market_share"]
