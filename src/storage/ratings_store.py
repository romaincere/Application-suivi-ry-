"""Notes manuelles par ticker (Moat, parts de marché…) stockées chiffrées."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st
from cryptography.fernet import Fernet, InvalidToken

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "manual_ratings.enc"


def _get_cipher() -> Fernet | None:
    try:
        key = st.secrets["fernet_key"]
    except (KeyError, FileNotFoundError):
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def load_ratings() -> dict[str, dict[str, int]]:
    """{ticker: {indicator_key: score_0_50_100}}"""
    cipher = _get_cipher()
    if cipher is None or not DATA_PATH.exists():
        return {}
    try:
        decrypted = cipher.decrypt(DATA_PATH.read_bytes())
    except InvalidToken:
        return {}
    return json.loads(decrypted.decode("utf-8"))


def save_ratings(ratings: dict[str, dict[str, int]]) -> None:
    cipher = _get_cipher()
    if cipher is None:
        st.error("Clé Fernet manquante : sauvegarde impossible.")
        return
    payload = json.dumps(ratings, ensure_ascii=False).encode("utf-8")
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_bytes(cipher.encrypt(payload))


def set_rating(ticker: str, indicator_key: str, score: int | None) -> None:
    ratings = load_ratings()
    ticker = ticker.upper()
    if score is None:
        if ticker in ratings and indicator_key in ratings[ticker]:
            del ratings[ticker][indicator_key]
            if not ratings[ticker]:
                del ratings[ticker]
    else:
        ratings.setdefault(ticker, {})[indicator_key] = int(score)
    save_ratings(ratings)


def get_rating(ticker: str, indicator_key: str) -> int | None:
    return load_ratings().get(ticker.upper(), {}).get(indicator_key)
