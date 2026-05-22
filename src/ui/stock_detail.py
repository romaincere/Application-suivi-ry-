"""Fiche détaillée d'une action : score, radar, financials, qualitatif, thèse."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data.market import get_financials, get_info
from src.screener.indicators import (
    CATEGORIES,
    INDICATORS,
    MANUAL_RATINGS_UI,
)
from src.screener.scorer import score_ticker
from src.storage.ratings_store import load_ratings, set_rating
from src.storage.thesis_store import get_thesis, save_thesis

VERDICT_COLORS = {
    "excellent": "#00C49A",
    "good": "#7DD3A8",
    "neutral": "#F4C542",
    "bad": "#E74C3C",
}


def _score_color(score: float | None) -> str:
    if score is None:
        return "#666666"
    if score >= 75:
        return VERDICT_COLORS["excellent"]
    if score >= 50:
        return VERDICT_COLORS["good"]
    if score >= 25:
        return VERDICT_COLORS["neutral"]
    return VERDICT_COLORS["bad"]


def _radar(category_scores: dict[str, float | None]) -> go.Figure:
    cats = [c for c in CATEGORIES if category_scores.get(c) is not None]
    values = [category_scores[c] for c in cats]
    if not cats:
        return go.Figure()
    cats_closed = cats + [cats[0]]
    values_closed = values + [values[0]]
    fig = go.Figure(
        go.Scatterpolar(
            r=values_closed,
            theta=cats_closed,
            fill="toself",
            fillcolor="rgba(0, 196, 154, 0.45)",
            line=dict(color="#00C49A", width=2),
        )
    )
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color="#888"),
                            gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(tickfont=dict(color="#FAFAFA", size=12),
                             gridcolor="rgba(255,255,255,0.1)"),
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=20, b=20),
        height=340,
    )
    return fig


def _financials_chart(ticker: str) -> go.Figure | None:
    fin = get_financials(ticker)
    if fin is None or fin.empty:
        return None

    def _row(*aliases):
        for n in aliases:
            if n in fin.index:
                return fin.loc[n].dropna().sort_index()
        return None

    revenue = _row("Total Revenue", "Revenue")
    op_income = _row("Operating Income", "EBIT")
    net_income = _row("Net Income", "Net Income Common Stockholders")
    if revenue is None or len(revenue) < 2:
        return None
    years = [d.year for d in revenue.index]
    fig = go.Figure()
    fig.add_bar(name="Chiffre d'affaires", x=years, y=revenue.values / 1e6,
                marker_color="#4A4A4A")
    if op_income is not None:
        fig.add_bar(name="Résultat d'exploitation", x=[d.year for d in op_income.index],
                    y=op_income.values / 1e6, marker_color="#F4C542")
    if net_income is not None:
        fig.add_bar(name="Résultat net", x=[d.year for d in net_income.index],
                    y=net_income.values / 1e6, marker_color="#00C49A")
        margin = (net_income / revenue.reindex(net_income.index)).dropna() * 100
        fig.add_scatter(name="Marge nette (%)", x=[d.year for d in margin.index],
                        y=margin.values, yaxis="y2", mode="lines+markers",
                        line=dict(color="#7DD3A8", width=2))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=340,
        yaxis=dict(title="Millions (devise locale)", gridcolor="rgba(255,255,255,0.08)"),
        yaxis2=dict(title="Marge nette %", overlaying="y", side="right",
                    showgrid=False, ticksuffix=" %"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=20, b=40),
        font=dict(color="#FAFAFA"),
    )
    return fig


def _fair_value_bar(current: float, target: float, currency: str) -> go.Figure:
    upside = (target - current) / current * 100 if current else 0
    fig = go.Figure()
    fig.add_shape(type="rect", x0=-30, x1=-5, y0=0, y1=1,
                  fillcolor="#00C49A", line=dict(width=0), opacity=0.85)
    fig.add_shape(type="rect", x0=-5, x1=5, y0=0, y1=1,
                  fillcolor="#F4C542", line=dict(width=0), opacity=0.85)
    fig.add_shape(type="rect", x0=5, x1=30, y0=0, y1=1,
                  fillcolor="#E74C3C", line=dict(width=0), opacity=0.85)
    fig.add_annotation(x=-17.5, y=0.5, text="Sous-évaluée",
                       showarrow=False, font=dict(color="white", size=12))
    fig.add_annotation(x=0, y=0.5, text="Prix correct",
                       showarrow=False, font=dict(color="black", size=12))
    fig.add_annotation(x=17.5, y=0.5, text="Surévaluée",
                       showarrow=False, font=dict(color="white", size=12))
    # Position du cours actuel (upside négatif → à droite ; positif → à gauche)
    marker_x = max(min(-upside, 30), -30)
    fig.add_vline(x=marker_x, line=dict(color="white", width=3))
    fig.add_annotation(x=marker_x, y=1.3,
                       text=f"<b>Cours {current:.2f} {currency}</b><br>Cible {target:.2f} {currency} · {upside:+.1f} %",
                       showarrow=False, font=dict(color="#FAFAFA", size=13))
    fig.update_xaxes(range=[-32, 32], visible=False)
    fig.update_yaxes(range=[0, 1.8], visible=False)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=130, margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def _manual_rating_bar(label: str, scale: list[str], score: int | None) -> None:
    pct = score if score is not None else 0
    color = _score_color(score)
    st.markdown(f"**{label}**")
    bar_html = f"""
    <div style="background:#1A1F2C;border-radius:8px;height:18px;position:relative;overflow:hidden;">
      <div style="width:{pct}%;height:100%;background:{color};transition:width .4s;"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:#888;margin-top:2px;">
      <span>{scale[0]}</span><span>{scale[1]}</span><span>{scale[2]}</span>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)


def _key_metrics(score_data: dict, info: dict) -> None:
    """Cards d'indicateurs clés (style 'Indicateurs clés' de la fiche)."""
    ind = score_data["indicators"]

    def _val(key: str) -> str:
        cell = ind.get(key, {})
        v = cell.get("value")
        if v is None:
            return "—"
        try:
            return cell["fmt"].format(v)
        except (KeyError, ValueError):
            return f"{v:.2f}"

    cards = [
        ("Croissance CA 5A", "cagr_5y"),
        ("Croissance EPS", "eps_growth"),
        ("FCF (croissance)", "fcf_trend"),
        ("Marge nette", "net_margin"),
        ("ROE", "roe"),
        ("ROIC", "roic"),
        ("PER", "pe"),
        ("Debt / Equity", "debt_equity"),
        ("Rendement dividende", "div_yield"),
        ("Croissance dividende", "div_growth"),
    ]
    cols = st.columns(5)
    for i, (label, key) in enumerate(cards):
        with cols[i % 5]:
            st.metric(label, _val(key))


def render(ticker: str, on_back) -> None:
    """Affiche la fiche détaillée pour `ticker`. `on_back` ferme la fiche."""
    info = get_info(ticker)
    score_data = score_ticker(ticker)

    # ── Header ──────────────────────────────────────────────────────
    c_back, c_title, c_score = st.columns([1, 4, 2])
    if c_back.button("← Retour", use_container_width=True):
        on_back()
        st.rerun()

    name = score_data["name"]
    sector = info.get("sector") or ""
    c_title.markdown(f"## {name}")
    c_title.caption(f"`{ticker}` · {sector}" if sector else f"`{ticker}`")

    gs = score_data["global_score"]
    gs_str = f"{gs:.0f}" if gs is not None else "—"
    c_score.markdown(
        f"<div style='text-align:right;'>"
        f"<div style='font-size:14px;color:#888;'>SCORE GLOBAL</div>"
        f"<div style='font-size:48px;font-weight:700;color:{_score_color(gs)};line-height:1;'>{gs_str}<span style='font-size:18px;color:#888;'> / 100</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Radar + Indicateurs clés ────────────────────────────────────
    col_radar, col_metrics = st.columns([1, 2])
    with col_radar:
        st.markdown("### Évaluation par catégorie")
        st.plotly_chart(_radar(score_data["category_scores"]),
                        use_container_width=True, config={"displayModeBar": False})
    with col_metrics:
        st.markdown("### Indicateurs clés")
        _key_metrics(score_data, info)

    st.divider()

    # ── Résultats financiers ────────────────────────────────────────
    st.markdown("### Résultats financiers")
    chart = _financials_chart(ticker)
    if chart is not None:
        st.plotly_chart(chart, use_container_width=True,
                        config={"displayModeBar": False})
    else:
        st.info("Données financières historiques indisponibles pour ce ticker.")

    st.divider()

    # ── Estimation juste valeur ─────────────────────────────────────
    st.markdown("### Estimation juste valeur")
    target = info.get("targetMeanPrice") or info.get("targetMedianPrice")
    current = info.get("currentPrice") or info.get("regularMarketPrice")
    currency = info.get("currency") or "EUR"
    if target and current:
        st.plotly_chart(_fair_value_bar(float(current), float(target), currency),
                        use_container_width=True, config={"displayModeBar": False})
        n_analysts = info.get("numberOfAnalystOpinions")
        if n_analysts:
            st.caption(f"Cible consensus de {n_analysts} analystes (Yahoo Finance).")
    else:
        st.info("Pas de target consensus disponible pour ce ticker "
                "(souvent le cas hors mega-caps).")

    st.divider()

    # ── Critères qualitatifs (manuels) ──────────────────────────────
    st.markdown("### Critères qualitatifs")
    st.caption(
        "Notation manuelle : ces critères ne sont pas calculables automatiquement. "
        "Mets à jour avec ton appréciation."
    )

    ratings = load_ratings().get(ticker.upper(), {})

    col_view, col_edit = st.columns([1, 1])
    with col_view:
        st.markdown("**Vue actuelle**")
        for r in MANUAL_RATINGS_UI:
            _manual_rating_bar(r["label"], r["scale"], ratings.get(r["key"]))

    with col_edit:
        st.markdown("**Modifier**")
        options = ["—", "Faible (0)", "Moyen (50)", "Fort (100)"]
        score_map = {"Faible (0)": 0, "Moyen (50)": 50, "Fort (100)": 100, "—": None}
        with st.form(f"manual_form_{ticker}"):
            new_values = {}
            for r in MANUAL_RATINGS_UI:
                current_score = ratings.get(r["key"])
                default_idx = 0
                if current_score == 0:
                    default_idx = 1
                elif current_score == 50:
                    default_idx = 2
                elif current_score == 100:
                    default_idx = 3
                new_values[r["key"]] = st.selectbox(
                    r["label"], options, index=default_idx, key=f"sel_{ticker}_{r['key']}"
                )
            if st.form_submit_button("💾 Enregistrer les notes"):
                for k, v in new_values.items():
                    set_rating(ticker, k, score_map[v])
                st.cache_data.clear()
                st.success("Notes enregistrées.")
                st.rerun()

    st.divider()

    # ── Thèse d'investissement ──────────────────────────────────────
    st.markdown("### Thèse d'investissement")
    current_thesis = get_thesis(ticker)
    with st.form(f"thesis_form_{ticker}"):
        new_thesis = st.text_area(
            "Pourquoi cette action ? (stocké chiffré)",
            value=current_thesis,
            height=150,
            placeholder="Ex. : Leader de l'efficacité énergétique, exposition data centers, "
                        "transition énergétique mondiale, ROIC élevé…",
            label_visibility="collapsed",
        )
        if st.form_submit_button("💾 Enregistrer la thèse"):
            save_thesis(ticker, new_thesis)
            st.success("Thèse enregistrée.")
            st.rerun()

    # ── Détail des 21 indicateurs ──────────────────────────────────
    with st.expander("🔬 Détail des 21 indicateurs"):
        rows = []
        for ind in INDICATORS:
            cell = score_data["indicators"].get(ind.key, {})
            v = cell.get("value")
            try:
                val_str = ind.fmt.format(v) if v is not None else "—"
            except (ValueError, TypeError):
                val_str = str(v)
            rows.append({
                "Catégorie": ind.category,
                "Indicateur": ind.label,
                "Valeur": val_str,
                "Note /100": cell.get("score"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
