"""Page Portefeuille : KPIs, tableau des positions, ajout/suppression."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.portfolio.calculator import aggregate, enrich_position
from src.storage.portfolio_store import DATA_PATH, load_portfolio, save_portfolio


def _format_money(value: float | None, currency: str = "EUR") -> str:
    if value is None:
        return "—"
    symbol = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF"}.get(currency, currency)
    return f"{value:,.2f} {symbol}".replace(",", " ")


def _kpis(agg: dict) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Valeur du portefeuille",
        _format_money(agg["value"], "EUR"),
        help="Valorisation actuelle de toutes tes positions, convertie en EUR.",
    )
    pnl = agg["pnl"]
    pnl_pct = agg["pnl_pct"]
    pnl_str = _format_money(pnl, "EUR") if pnl is not None else "—"
    delta_pnl = f"{pnl_pct:+.2f}%" if pnl_pct is not None else None
    c2.metric(
        "Plus-value (€)",
        pnl_str,
        delta=delta_pnl,
        help="Plus-value latente : différence entre la valeur actuelle et le capital investi.",
    )
    pnl_pct_str = f"{pnl_pct:+.2f} %" if pnl_pct is not None else "—"
    c3.metric(
        "Plus-value (%)",
        pnl_pct_str,
        help="Performance globale du portefeuille depuis l'achat.",
    )


def _positions_table(enriched: list) -> None:
    if not enriched:
        st.info("Aucune position. Ajoute ta première ligne ci-dessous 👇")
        return

    rows = []
    total_value_eur = sum(p.value_eur for p in enriched if p.value_eur is not None) or 0
    for p in enriched:
        weight = (p.value_eur / total_value_eur * 100) if (p.value_eur and total_value_eur) else None
        rows.append(
            {
                "Ticker": p.ticker,
                "Nom": p.name,
                "Qté": p.quantity,
                "PRU": p.purchase_price,
                "Cours actuel": p.price,
                "Devise": p.currency,
                "Valeur (€)": p.value_eur,
                "Plus-value (€)": p.pnl_eur,
                "Plus-value (%)": p.pnl_pct,
                "Poids (%)": weight,
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Qté": st.column_config.NumberColumn(format="%.2f"),
            "PRU": st.column_config.NumberColumn(
                format="%.2f", help="Prix d'achat dans la devise native de l'action."
            ),
            "Cours actuel": st.column_config.NumberColumn(
                format="%.2f", help="Cours en temps réel dans la devise native."
            ),
            "Valeur (€)": st.column_config.NumberColumn(
                format="%.2f €", help="Valorisation convertie en euros."
            ),
            "Plus-value (€)": st.column_config.NumberColumn(
                format="%.2f €", help="Plus-value latente en euros."
            ),
            "Plus-value (%)": st.column_config.NumberColumn(format="%+.2f%%"),
            "Poids (%)": st.column_config.ProgressColumn(
                format="%.1f%%", min_value=0, max_value=100
            ),
        },
    )


def _add_position_form(positions: list[dict]) -> None:
    with st.expander("➕ Ajouter une position", expanded=not positions):
        with st.form("add_position", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
            ticker = c1.text_input(
                "Ticker",
                placeholder="AAPL, MC.PA, CW8.PA…",
                help="Format Yahoo Finance. Suffixes : `.PA` pour Paris, `.DE` pour Francfort, etc.",
            )
            quantity = c2.number_input("Quantité", min_value=0.0, step=1.0, format="%.4f")
            purchase_price = c3.number_input(
                "Prix d'achat (PRU)", min_value=0.0, step=0.01, format="%.2f"
            )
            purchase_date = c4.date_input("Date d'achat", value=date.today())

            submitted = st.form_submit_button("Ajouter", use_container_width=True)
            if submitted:
                if not ticker or quantity <= 0 or purchase_price <= 0:
                    st.error("Renseigne au moins ticker, quantité et prix d'achat.")
                    return
                positions.append(
                    {
                        "ticker": ticker.strip().upper(),
                        "quantity": float(quantity),
                        "purchase_price": float(purchase_price),
                        "purchase_date": purchase_date.isoformat(),
                    }
                )
                save_portfolio(positions)
                st.success(f"{ticker} ajouté.")
                st.rerun()


def _delete_position_form(positions: list[dict]) -> None:
    if not positions:
        return
    with st.expander("🗑️ Supprimer une position"):
        labels = [
            f"{p['ticker']} — {p['quantity']:g} @ {p['purchase_price']:g} ({p.get('purchase_date', '')})"
            for p in positions
        ]
        idx = st.selectbox(
            "Position à supprimer", range(len(labels)), format_func=lambda i: labels[i]
        )
        if st.button("Supprimer", type="primary"):
            removed = positions.pop(idx)
            save_portfolio(positions)
            st.success(f"{removed['ticker']} supprimé.")
            st.rerun()


def _backup_controls(positions: list[dict]) -> None:
    """Export/import du fichier chiffré (Streamlit Cloud = stockage éphémère)."""
    with st.expander("💾 Sauvegarde / Restauration"):
        st.caption(
            "Le stockage Streamlit Cloud est éphémère : pense à télécharger un backup "
            "régulièrement et après chaque modification importante."
        )
        c1, c2 = st.columns(2)
        if DATA_PATH.exists():
            c1.download_button(
                "⬇️ Télécharger le backup chiffré",
                data=DATA_PATH.read_bytes(),
                file_name="portfolio.enc",
                mime="application/octet-stream",
                use_container_width=True,
            )
        uploaded = c2.file_uploader(
            "⬆️ Restaurer un backup", type=None, label_visibility="collapsed"
        )
        if uploaded is not None:
            DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            DATA_PATH.write_bytes(uploaded.read())
            st.success("Backup restauré. Recharge la page.")
            st.rerun()


def render() -> None:
    st.title("📊 Mon Portefeuille")

    positions = load_portfolio()
    enriched = [enrich_position(p) for p in positions] if positions else []
    agg = (
        aggregate(enriched)
        if enriched
        else {"value": 0.0, "cost": 0.0, "pnl": None, "pnl_pct": None, "n_positions": 0}
    )

    _kpis(agg)
    st.divider()
    _positions_table(enriched)

    st.divider()
    _add_position_form(positions)
    _delete_position_form(positions)
    _backup_controls(positions)
