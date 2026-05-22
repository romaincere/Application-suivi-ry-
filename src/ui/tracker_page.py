"""Tracker PEA : scan multi-marchés + sélection d'une ligne → fiche détaillée."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.ai_ratings import is_configured as ai_ready
from src.data.finnhub import is_configured as finnhub_ready
from src.screener.indicators import CATEGORIES, INDICATORS
from src.screener.scorer import score_universe
from src.screener.universe import UNIVERSES
from src.ui import stock_detail

SELECTED_KEY = "tracker_selected_ticker"
RESULTS_KEY = "tracker_results"
UNIVERSE_KEY = "tracker_last_universe"


def _select_ticker(ticker: str) -> None:
    st.session_state[SELECTED_KEY] = ticker


def _clear_selection() -> None:
    st.session_state.pop(SELECTED_KEY, None)


def _build_summary_df(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        row = {
            "Ticker": r["ticker"],
            "Nom": r["name"],
            "Score": r["global_score"],
            "N. ind.": r["n_available"],
        }
        for cat in CATEGORIES:
            row[cat] = r["category_scores"].get(cat)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.insert(0, "Rang", range(1, len(df) + 1))
    return df


def _build_detail_df(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        row = {"Ticker": r["ticker"], "Nom": r["name"], "Score": r["global_score"]}
        for ind in INDICATORS:
            cell = r["indicators"].get(ind.key, {})
            v = cell.get("value")
            try:
                row[ind.label] = ind.fmt.format(v) if v is not None else "—"
            except (ValueError, TypeError):
                row[ind.label] = str(v)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.insert(0, "Rang", range(1, len(df) + 1))
    return df


def _column_config(score_cols: list[str]) -> dict:
    cfg = {
        "Score": st.column_config.ProgressColumn(
            "Score /100", format="%.0f", min_value=0, max_value=100
        ),
    }
    for c in score_cols:
        if c != "Score":
            cfg[c] = st.column_config.ProgressColumn(
                format="%.0f", min_value=0, max_value=100
            )
    return cfg


def _render_tracker_view() -> None:
    st.title("🇪🇺 Tracker PEA")
    st.caption(
        f"Note chaque action sur 100 selon {len(INDICATORS)} indicateurs "
        "(croissance, rentabilité, valorisation, solidité, momentum, dividende, qualité). "
        "Univers limités aux actions éligibles au PEA. Clique sur une ligne pour la fiche détaillée."
    )

    if not finnhub_ready():
        st.info(
            "💡 L'indicateur **Insider Buying** sera disponible si tu ajoutes une clé "
            "Finnhub gratuite dans les Secrets Streamlit."
        )
    if not ai_ready():
        st.info(
            "💡 Les critères **Moat / Qualité management / Parts de marché** seront "
            "estimés par IA si tu ajoutes une clé Anthropic dans les Secrets."
        )

    # ── Choix de l'univers ──────────────────────────────────────────
    universe_choices = list(UNIVERSES.keys()) + ["Liste personnalisée"]
    c1, c2 = st.columns([2, 1])
    choice = c1.selectbox("Univers à scanner", universe_choices)

    if choice == "Liste personnalisée":
        custom = c1.text_area(
            "Tickers séparés par des virgules ou retours à la ligne",
            placeholder="MC.PA, SAP.DE, ASML.AS…",
            height=100,
        )
        tickers = [t.strip().upper() for t in custom.replace("\n", ",").split(",") if t.strip()]
    else:
        tickers = UNIVERSES[choice]

    min_score = c2.slider("Score minimum à afficher", 0, 100, 0, 5)
    n = len(tickers)
    if not tickers:
        return

    use_ai = False
    if ai_ready():
        use_ai = st.checkbox(
            "🤖 Activer l'estimation IA (Moat / Management / Parts de marché)",
            value=True,
            help="Utilise Claude pour estimer les 3 critères qualitatifs non couverts "
                 "par yfinance. Coût ~$0.005 par action, cache 7 jours.",
        )

    base_min = max(1, n // 8)
    estimate = base_min + (n // 3 if use_ai else 0)
    st.caption(f"📊 {n} tickers · 1er scan ≈ {estimate} min (cache ensuite).")

    if st.button("🚀 Lancer le scan", type="primary"):
        progress = st.progress(0.0, text="Démarrage…")

        def _cb(pct: float, ticker: str) -> None:
            progress.progress(pct, text=f"Analyse {ticker} ({int(pct * n)}/{n})")

        results = score_universe(tickers, progress_cb=_cb, use_ai=use_ai)
        progress.empty()
        st.session_state[RESULTS_KEY] = results
        st.session_state[UNIVERSE_KEY] = choice

    results = st.session_state.get(RESULTS_KEY)
    if not results:
        st.info("Clique sur **Lancer le scan** pour démarrer l'analyse.")
        return

    filtered = [r for r in results if (r["global_score"] or 0) >= min_score]
    if not filtered:
        st.warning("Aucune action ne dépasse le score minimum demandé.")
        return

    # ── KPIs ────────────────────────────────────────────────────────
    scored = [r for r in filtered if r["global_score"] is not None]
    avg = sum(r["global_score"] for r in scored) / len(scored) if scored else 0
    top = scored[0] if scored else None
    k1, k2, k3 = st.columns(3)
    k1.metric("Actions analysées", f"{len(filtered)} / {n}")
    k2.metric("Score moyen", f"{avg:.0f} / 100")
    if top:
        k3.metric("🏆 Meilleur score",
                  f"{top['ticker']} — {top['global_score']:.0f}",
                  help=top["name"])

    st.caption("👇 **Clique sur une ligne pour ouvrir la fiche détaillée.**")

    # ── Tableau interactif ──────────────────────────────────────────
    tab1, tab2 = st.tabs(["📋 Vue résumée", "🔬 Détail des indicateurs"])

    with tab1:
        df = _build_summary_df(filtered)
        event = st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config=_column_config(["Score"] + CATEGORIES),
            selection_mode="single-row", on_select="rerun", key="summary_tbl",
        )
        if event and event.selection.rows:
            _select_ticker(filtered[event.selection.rows[0]]["ticker"])
            st.rerun()

    with tab2:
        df_detail = _build_detail_df(filtered)
        event = st.dataframe(
            df_detail, use_container_width=True, hide_index=True,
            column_config=_column_config(["Score"]),
            selection_mode="single-row", on_select="rerun", key="detail_tbl",
        )
        if event and event.selection.rows:
            _select_ticker(filtered[event.selection.rows[0]]["ticker"])
            st.rerun()
        st.download_button(
            "⬇️ Exporter en CSV",
            data=df_detail.to_csv(index=False).encode("utf-8"),
            file_name="tracker_pea.csv", mime="text/csv",
        )


def render() -> None:
    selected = st.session_state.get(SELECTED_KEY)
    if selected:
        stock_detail.render(selected, on_back=_clear_selection)
    else:
        _render_tracker_view()
