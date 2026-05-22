"""Entrée Streamlit : Tracker PEA + fiches détaillées."""
from __future__ import annotations

import streamlit as st

from src.auth.password import require_password
from src.ui import tracker_page

st.set_page_config(
    page_title="Tracker PEA",
    page_icon="🇪🇺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Métadonnées pour "Ajouter à l'écran d'accueil" sur iOS/iPadOS et Android.
st.markdown(
    """
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Tracker PEA">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#0E1117">
    """,
    unsafe_allow_html=True,
)

require_password()

tracker_page.render()
