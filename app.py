"""Entrée Streamlit : suivi de portefeuille + screener d'actions."""
from __future__ import annotations

import streamlit as st

from src.auth.password import require_password
from src.ui import portfolio_page, screener_page

st.set_page_config(
    page_title="Mon Portefeuille",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Métadonnées pour "Ajouter à l'écran d'accueil" sur iOS/iPadOS et Android.
st.markdown(
    """
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Portefeuille">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#0E1117">
    """,
    unsafe_allow_html=True,
)

require_password()

PAGES = {
    "📊 Mon Portefeuille": portfolio_page.render,
    "🎯 Screener": screener_page.render,
}

with st.sidebar:
    st.title("📈 Suivi Portefeuille")
    choice = st.radio(
        "Navigation",
        list(PAGES.keys()),
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("MVP — Phase 1 (squelette)")

PAGES[choice]()
