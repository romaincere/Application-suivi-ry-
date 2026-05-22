"""Page Screener : scoring multi-indicateurs + classement."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.screener.indicators import CATEGORIES, INDICATORS
from src.screener.scorer import score_universe
from src.screener.universe import UNIVERSES
from src.storage.portfolio_store import load_portfolio


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


def render() -> None:
    st.title("🎯 Screener d'actions à fort potentiel")
    st.caption(
        "Note chaque action sur 100 selon 12 indicateurs (croissance, rentabilité, "
        "valorisation, solidité, momentum) et classe par score décroissant."
    )

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
            - Chaque indicateur disponible reçoit une note **0** (mauvais), **50** (neutre) ou **100** (excellent), d'après les seuils définis.
            - Le **score global** est la moyenne des notes disponibles (les indicateurs manquants sont ignorés, pas pénalisés).
            - Le **score par catégorie** est la moyenne des notes de cette catégorie.

            **Seuils par indicateur**

            | Catégorie | Indicateur | Excellent | Neutre | Mauvais |
            |---|---|---|---|---|
            | Croissance | Croissance CA | >15% | 5-15% | <5% |
            | Croissance | Croissance EPS | >20% | 5-20% | <5% |
            | Rentabilité | ROE | >15% | 8-15% | <8% |
            | Rentabilité | Marge nette | >15% | 5-15% | <5% |
            | Valorisation | PER | 10-25 | 5-40 | >40 ou <5 |
            | Valorisation | PEG | <1.5 | 1.5-2.5 | >2.5 |
            | Valorisation | P/S | <5 | 5-10 | >10 |
            | Solidité | Debt/Equity | <1 | 1-2 | >2 |
            | Solidité | Current Ratio | >1.5 | 1-1.5 | <1 |
            | Momentum | MM50/MM200 | >1.0 (golden) | 0.98-1.0 | <0.98 |
            | Momentum | RSI 14 | 40-65 | 30-70 | <30 ou >70 |
            | Momentum | Perf 1A | >20% | 0-20% | <0% |

            Les indicateurs qualitatifs (Moat, Insider Buying, Parts de marché)
            ne sont pas inclus car non disponibles via yfinance.
            """
        )
