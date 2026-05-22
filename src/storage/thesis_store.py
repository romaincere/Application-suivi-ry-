"""Thèses d'investissement par ticker (texte libre chiffré)."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from cryptography.fernet import Fernet, InvalidToken

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "theses.enc"


def _get_cipher() -> Fernet | None:
    try:
        key = st.secrets["fernet_key"]
    except (KeyError, FileNotFoundError):
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def load_theses() -> dict[str, str]:
    cipher = _get_cipher()
    if cipher is None or not DATA_PATH.exists():
        return {}
    try:
        return json.loads(cipher.decrypt(DATA_PATH.read_bytes()).decode("utf-8"))
    except InvalidToken:
        return {}


def save_thesis(ticker: str, text: str) -> None:
    cipher = _get_cipher()
    if cipher is None:
        st.error("Clé Fernet manquante : sauvegarde impossible.")
        return
    theses = load_theses()
    ticker = ticker.upper()
    if text.strip():
        theses[ticker] = text.strip()
    else:
        theses.pop(ticker, None)
    payload = json.dumps(theses, ensure_ascii=False).encode("utf-8")
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_bytes(cipher.encrypt(payload))


def get_thesis(ticker: str) -> str:
    return load_theses().get(ticker.upper(), "")
