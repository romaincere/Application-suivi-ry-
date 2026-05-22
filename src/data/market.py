"""Wrapper yfinance avec cache Streamlit."""
from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=300, show_spinner=False)
def get_quote(ticker: str) -> dict | None:
    """Cote temps réel + nom + devise."""
    try:
        t = yf.Ticker(ticker)
        fast = t.fast_info
        info = t.info or {}
        return {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "price": float(fast.last_price) if fast.last_price else None,
            "currency": fast.currency or info.get("currency") or "EUR",
            "previous_close": (
                float(fast.previous_close) if fast.previous_close else None
            ),
        }
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def get_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Historique de cours (OHLCV)."""
    return yf.Ticker(ticker).history(
        period=period,
        interval=interval,
        auto_adjust=True,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_info(ticker: str) -> dict:
    """Métadonnées fondamentales (PER, capi, secteur, dividende...)."""
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


@st.cache_data(ttl=86400, show_spinner=False)
def get_financials(ticker: str) -> pd.DataFrame:
    """Compte de résultat annuel (4 dernières années)."""
    try:
        df = yf.Ticker(ticker).financials
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def get_balance_sheet(ticker: str) -> pd.DataFrame:
    """Bilan annuel (4 dernières années)."""
    try:
        df = yf.Ticker(ticker).balance_sheet
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def get_cashflow(ticker: str) -> pd.DataFrame:
    """Tableau de flux de trésorerie annuel (4 dernières années)."""
    try:
        df = yf.Ticker(ticker).cashflow
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def get_dividends(ticker: str) -> pd.Series:
    """Historique des versements de dividendes (date → montant)."""
    try:
        s = yf.Ticker(ticker).dividends
        return s if s is not None else pd.Series(dtype=float)
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=600, show_spinner=False)
def get_fx_rate(currency_from: str, currency_to: str = "EUR") -> float | None:
    """Taux de change : 1 unité de `currency_from` → N unités de `currency_to`.

    Utilise les tickers Yahoo `<base><quote>=X` (ex. `EURUSD=X` → combien de USD
    pour 1 EUR).
    """
    if currency_from == currency_to or not currency_from:
        return 1.0
    try:
        ticker = f"{currency_to}{currency_from}=X"
        rate = float(yf.Ticker(ticker).fast_info.last_price)
        if not rate:
            return None
        return 1.0 / rate
    except Exception:
        return None
