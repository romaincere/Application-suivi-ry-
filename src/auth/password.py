"""Mini auth par mot de passe stocké dans `st.secrets`."""
from __future__ import annotations

import streamlit as st


def _expected_password() -> str | None:
    try:
        return st.secrets["app_password"]
    except (KeyError, FileNotFoundError):
        return None


def require_password() -> None:
    """Bloque l'exécution tant que le bon mot de passe n'est pas saisi."""
    if st.session_state.get("authenticated"):
        return

    expected = _expected_password()
    if not expected:
        st.warning(
            "Aucun mot de passe configuré. Ajoute `app_password` dans "
            "`.streamlit/secrets.toml` (local) ou dans les Secrets de Streamlit Cloud."
        )
        st.session_state["authenticated"] = True
        return

    st.title("🔒 Accès protégé")
    st.caption("Saisis le mot de passe pour accéder à ton portefeuille.")
    pwd = st.text_input("Mot de passe", type="password", label_visibility="collapsed")

    if pwd:
        if pwd == expected:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")

    st.stop()
