"""Wrapper Finnhub : transactions d'initiés (insider buying)."""
from __future__ import annotations

from datetime import datetime, timedelta

import requests
import streamlit as st

BASE_URL = "https://finnhub.io/api/v1"


def _api_key() -> str | None:
    try:
        return st.secrets["finnhub_api_key"]
    except (KeyError, FileNotFoundError):
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def insider_transactions(ticker: str, months: int = 6) -> dict | None:
    """Retourne un résumé des transactions d'initiés sur N mois.

    {
      "purchases": int,   # nb actions achetées (transactionCode 'P')
      "sales": int,       # nb actions vendues (transactionCode 'S')
      "n_buyers": int,    # nb d'insiders distincts ayant acheté
      "n_sellers": int,
      "ratio": float,     # (purchases - sales) / (purchases + sales), ∈ [-1, 1]
    }
    """
    key = _api_key()
    if not key:
        return None

    since = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")
    try:
        r = requests.get(
            f"{BASE_URL}/stock/insider-transactions",
            params={"symbol": ticker, "from": since, "token": key},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        data = r.json().get("data") or []
    except Exception:
        return None

    purchases = sales = 0
    buyers, sellers = set(), set()
    for tx in data:
        code = (tx.get("transactionCode") or "").upper()
        change = tx.get("change") or 0
        name = tx.get("name") or ""
        if code == "P" or (code != "S" and change > 0):
            purchases += abs(change)
            if name:
                buyers.add(name)
        elif code == "S" or (code != "P" and change < 0):
            sales += abs(change)
            if name:
                sellers.add(name)

    total = purchases + sales
    ratio = (purchases - sales) / total if total else None

    return {
        "purchases": purchases,
        "sales": sales,
        "n_buyers": len(buyers),
        "n_sellers": len(sellers),
        "ratio": ratio,
    }


def is_configured() -> bool:
    return _api_key() is not None
