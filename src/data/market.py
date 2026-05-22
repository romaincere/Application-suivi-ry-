"""Wrapper yfinance avec cache Streamlit."""
from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=300, show_spinner=False)
def get_quote(ticker: str) -> dict | None:
    """Cote temps réel (prix, devise, clôture précédente)."""
    try:
        fast = yf.Ticker(ticker).fast_info
        return {
            "ticker": ticker,
            "price": float(fast.last_price) if fast.last_price else None,
            "currency": fast.currency,
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
