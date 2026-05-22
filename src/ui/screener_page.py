"""Page Screener : scoring multi-indicateurs + classement."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.finnhub import is_configured as finnhub_ready
from src.screener.indicators import CATEGORIES, INDICATORS, MANUAL_KEYS
from src.screener.scorer import score_universe
from src.screener.universe import UNIVERSES
from src.storage.portfolio_store import load_portfolio
from src.storage.ratings_store import load_ratings, set_rating


def _score_color(score: float | None) -> str:
    if score is None:
        return "⚪"
    if score >= 70:
        return "🟢"
    if score >= 50:
        return "🟡"
    return "🔴"


def _fmt_indicator(value: float | None, fmt: str) -> str:
    if value is None:
        return "—"
    try:
        return fmt.format(value)
    except (ValueError, TypeError):
        return str(value)


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
            row[ind.label] = _fmt_indicator(cell.get("value"), ind.fmt)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.insert(0, "Rang", range(1, len(df) + 1))
    return df


def _render_table(df: pd.DataFrame, score_cols: list[str]) -> None:
    column_config = {
        "Score": st.column_config.ProgressColumn(
            "Score /100", format="%.0f", min_value=0, max_value=100
        ),
    }
    for c in score_cols:
        if c in df.columns and c != "Score":
            column_config[c] = st.column_config.ProgressColumn(
                format="%.0f", min_value=0, max_value=100
            )
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )


def _manual_ratings_form() -> None:
    """Formulaire pour noter manuellement Moat et Parts de marché par ticker."""
    with st.expander("✍️ Notes manuelles (Moat / Parts de marché)"):
        st.caption(
            "Ces deux indicateurs ne sont pas calculables automatiquement. "
            "Note ici les actions que tu suis : ces notes seront incluses dans le score global."
        )

        ratings = load_ratings()
        portfolio = load_portfolio()
        suggested = sorted({p["ticker"] for p in portfolio} | set(ratings.keys()))

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        ticker_input = c1.text_input(
            "Ticker", placeholder="AAPL, MC.PA…",
            help=f"Tickers déjà notés : {', '.join(suggested) if suggested else 'aucun'}",
        ).strip().upper()
        moat_options = ["—", "Faible (0)", "Moyen (50)", "Fort (100)"]
        moat_choice = c2.selectbox("Moat", moat_options, key="moat_select")
        ms_choice = c3.selectbox("Parts de marché", moat_options, key="ms_select")

        def _to_score(choice: str) -> int | None:
            return {"Faible (0)": 0, "Moyen (50)": 50, "Fort (100)": 100}.get(choice)

        if c4.button("Enregistrer", use_container_width=True):
            if not ticker_input:
                st.error("Saisis un ticker.")
            else:
                set_rating(ticker_input, "moat", _to_score(moat_choice))
                set_rating(ticker_input, "market_share", _to_score(ms_choice))
                # Invalide le cache du scorer pour ce ticker
                st.cache_data.clear()
                st.success(f"Notes enregistrées pour {ticker_input}.")
                st.rerun()

        if ratings:
            st.markdown("**Notes enregistrées :**")
            df = pd.DataFrame(
                [
                    {
                        "Ticker": t,
                        "Moat": r.get("moat", "—"),
                        "Parts de marché": r.get("market_share", "—"),
                    }
                    for t, r in sorted(ratings.items())
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)


def render() -> None:
    st.title("🎯 Screener d'actions à fort potentiel")
    st.caption(
        f"Note chaque action sur 100 selon {len(INDICATORS)} indicateurs "
        "(croissance, rentabilité, valorisation, solidité, momentum, qualité) "
        "et classe par score décroissant."
    )

    if not finnhub_ready():
        st.info(
            "💡 L'indicateur **Insider Buying** sera disponible si tu ajoutes une clé "
            "Finnhub gratuite (https://finnhub.io) dans `st.secrets['finnhub_api_key']`."
        )

    _manual_ratings_form()

    # ── Choix de l'univers ──────────────────────────────────────────
    portfolio = load_portfolio()
    portfolio_tickers = [p["ticker"] for p in portfolio] if portfolio else []

    universe_choices = list(UNIVERSES.keys()) + ["Mon portefeuille", "Liste personnalisée"]
    c1, c2 = st.columns([2, 1])
    choice = c1.selectbox("Univers à scanner", universe_choices)

    if choice == "Mon portefeuille":
        tickers = portfolio_tickers
        if not tickers:
            st.warning("Ton portefeuille est vide. Ajoute des positions d'abord.")
            return
    elif choice == "Liste personnalisée":
        custom = c1.text_area(
            "Tickers séparés par des virgules ou retours à la ligne",
            placeholder="AAPL, MSFT, MC.PA, NVDA…",
            height=100,
        )
        tickers = [t.strip().upper() for t in custom.replace("\n", ",").split(",") if t.strip()]
    else:
        tickers = UNIVERSES[choice]

    min_score = c2.slider("Score minimum à afficher", 0, 100, 0, 5)
    n_tickers = len(tickers)

    if not tickers:
        return

    info_msg = (
        f"📊 {n_tickers} tickers · 1er scan ≈ {max(1, n_tickers // 10)} min "
        "(appels yfinance + cache 1h ensuite)."
    )
    st.caption(info_msg)

    if not st.button("🚀 Lancer le scan", type="primary"):
        st.info("Clique sur **Lancer le scan** pour démarrer l'analyse.")
        return

    # ── Scan ────────────────────────────────────────────────────────
    progress = st.progress(0.0, text="Démarrage…")

    def _cb(pct: float, ticker: str) -> None:
        progress.progress(pct, text=f"Analyse {ticker} ({int(pct * n_tickers)}/{n_tickers})")

    results = score_universe(tickers, progress_cb=_cb)
    progress.empty()

    # Filtre score min
    filtered = [r for r in results if (r["global_score"] or 0) >= min_score]
    if not filtered:
        st.warning("Aucune action ne dépasse le score minimum demandé.")
        return

    # ── KPIs ────────────────────────────────────────────────────────
    scored = [r for r in filtered if r["global_score"] is not None]
    avg = sum(r["global_score"] for r in scored) / len(scored) if scored else 0
    top = scored[0] if scored else None
    k1, k2, k3 = st.columns(3)
    k1.metric("Actions analysées", f"{len(filtered)} / {n_tickers}")
    k2.metric("Score moyen", f"{avg:.0f} / 100")
    if top:
        k3.metric(
            "🏆 Meilleur score",
            f"{top['ticker']} — {top['global_score']:.0f}",
            help=top["name"],
        )

    st.divider()

    # ── Vue résumée par catégorie ───────────────────────────────────
    tab1, tab2 = st.tabs(["📋 Vue résumée", "🔬 Détail des indicateurs"])

    with tab1:
        st.markdown("**Score global et par catégorie** (du meilleur au pire).")
        summary = _build_summary_df(filtered)
        _render_table(summary, score_cols=["Score"] + CATEGORIES)

    with tab2:
        st.markdown("**Valeurs brutes des 12 indicateurs**.")
        detail = _build_detail_df(filtered)
        _render_table(detail, score_cols=["Score"])
        st.download_button(
            "⬇️ Exporter en CSV",
            data=detail.to_csv(index=False).encode("utf-8"),
            file_name="screener_results.csv",
            mime="text/csv",
        )

    # ── Légende ─────────────────────────────────────────────────────
    with st.expander("ℹ️ Comment lire le score"):
        st.markdown(
            """
            **Méthodologie**
            - Chaque indicateur disponible reçoit une note **0** (mauvais), **50** (neutre) ou **100** (excellent).
            - Le **score global** est la moyenne des notes disponibles (les indicateurs manquants sont ignorés).
            - Le **score par catégorie** est la moyenne des notes de cette catégorie.

            **Seuils par indicateur**

            | Catégorie | Indicateur | Excellent | Neutre | Mauvais | Source |
            |---|---|---|---|---|---|
            | Croissance | Croissance CA | >15% | 5-15% | <5% | yfinance |
            | Croissance | Croissance EPS | >20% | 5-20% | <5% | yfinance |
            | Croissance | CAGR CA 5A | >15% | 5-15% | <5% | yfinance financials |
            | Rentabilité | ROE | >15% | 8-15% | <8% | yfinance |
            | Rentabilité | ROIC | >12% | 6-12% | <6% | yfinance financials + balance |
            | Rentabilité | Marge nette | >15% | 5-15% | <5% | yfinance |
            | Valorisation | PER | 10-25 | 5-40 | >40 ou <5 | yfinance |
            | Valorisation | PEG | <1.5 | 1.5-2.5 | >2.5 | yfinance |
            | Valorisation | Price/Sales | <5 | 5-10 | >10 | yfinance |
            | Solidité | Debt/Equity | <1 | 1-2 | >2 | yfinance |
            | Solidité | FCF (croissance) | >15% / an | 0-15% | <0 ou négatif | yfinance cashflow |
            | Solidité | Current Ratio | >1.5 | 1-1.5 | <1 | yfinance |
            | Momentum | MM50/MM200 | >1.0 | 0.98-1.0 | <0.98 | yfinance history |
            | Momentum | RSI 14 | 40-65 | 30-70 | <30 ou >70 | yfinance history |
            | Momentum | Performance 1A | >20% | 0-20% | <0% | yfinance history |
            | Qualité | Moat | Note manuelle 100 | 50 | 0 | Saisie manuelle |
            | Qualité | Insider Buying | ratio >0.3 | -0.3 à 0.3 | <-0.3 | Finnhub (clé API) |
            | Qualité | Parts de marché | Note manuelle 100 | 50 | 0 | Saisie manuelle |
            """
        )
