"""Stockage chiffré (Fernet) du portefeuille.

Le fichier `data/portfolio.enc` est versionné dans le repo ; sans la clé
Fernet stockée dans `st.secrets["fernet_key"]` son contenu est illisible.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st
from cryptography.fernet import Fernet, InvalidToken

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "portfolio.enc"


def _get_cipher() -> Fernet | None:
    try:
        key = st.secrets["fernet_key"]
    except (KeyError, FileNotFoundError):
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def load_portfolio() -> list[dict[str, Any]]:
    cipher = _get_cipher()
    if cipher is None or not DATA_PATH.exists():
        return []
    try:
        decrypted = cipher.decrypt(DATA_PATH.read_bytes())
    except InvalidToken:
        st.error("Impossible de déchiffrer le portefeuille (clé Fernet invalide).")
        return []
    return json.loads(decrypted.decode("utf-8"))


def save_portfolio(positions: list[dict[str, Any]]) -> None:
    cipher = _get_cipher()
    if cipher is None:
        st.error("Clé Fernet manquante : sauvegarde impossible.")
        return
    payload = json.dumps(positions, ensure_ascii=False).encode("utf-8")
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_bytes(cipher.encrypt(payload))


def generate_key() -> str:
    """Helper CLI : génère une clé Fernet à coller dans les secrets."""
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    print(generate_key())
