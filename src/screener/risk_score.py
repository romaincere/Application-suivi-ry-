"""Risk score « école Buffett/Munger × Graham » sur 100 points.

Repondère les indicateurs déjà calculés par `scorer.score_ticker` en
4 piliers pondérés, puis en déduit un verdict de risque, des étoiles et
les chiffres clés. Logique 100 % déterministe : fonctionne sans clé API.

Convention : un score ÉLEVÉ = entreprise de qualité achetée à bon prix
            = risque FAIBLE. Le verdict inverse donc l'échelle.
"""
from __future__ import annotations

from typing import Any

# ── Définition des 4 piliers ────────────────────────────────────────
# weight = points max du pilier ; keys = indicateurs (clés de INDICATORS)
# agrégés en moyenne des notes ∈ {0,50,100} disponibles.
PILLARS: list[dict[str, Any]] = [
    {
        "key": "valuation",
        "label": "Valorisation",
        "weight": 30,
        "keys": ["pe", "peg", "ps", "upside"],
        "hint": "P/E, PEG, P/S, décote vs juste prix consensus.",
    },
    {
        "key": "financial_health",
        "label": "Santé financière",
        "weight": 30,
        "keys": ["debt_equity", "fcf_trend", "current_ratio"],
        "hint": "Dette/fonds propres, tendance du FCF, liquidité.",
    },
    {
        "key": "growth",
        "label": "Croissance",
        "weight": 25,
        "keys": ["revenue_growth", "eps_growth", "cagr_5y", "revenue_predictability"],
        "hint": "Croissance CA & EPS, CAGR 5 ans, prévisibilité.",
    },
    {
        "key": "quality_moat",
        "label": "Qualité & moat",
        "weight": 15,
        "keys": ["moat", "management_quality", "market_share",
                 "capital_allocation", "roe", "roic", "net_margin"],
        "hint": "Moat, ROE/ROIC, marge, allocation du capital.",
    },
]

# Chiffres clés affichés en priorité (les 5 premiers disponibles).
KEY_FIGURE_ORDER: list[str] = [
    "pe", "upside", "cagr_5y", "fcf_trend", "roic",
    "roe", "net_margin", "debt_equity", "eps_growth", "div_yield",
]


def _stars(score_0_100: float | None) -> tuple[float, str]:
    """Convertit une note /100 en (n_étoiles_sur_5, rendu unicode)."""
    if score_0_100 is None:
        return 0.0, "☆☆☆☆☆"
    n = round(score_0_100 / 20 * 2) / 2  # arrondi au demi
    full = int(n)
    half = 1 if (n - full) >= 0.5 else 0
    empty = 5 - full - half
    return n, "★" * full + ("½" if half else "") + "☆" * empty


def compute_risk_score(score_data: dict[str, Any]) -> dict[str, Any]:
    """À partir du dict renvoyé par `score_ticker`, calcule le risk score.

    Retourne :
      {
        total: float|None,            # /100 pondéré
        pillars: [ {key,label,weight,score,points,stars,n,stars_str,hint} ],
        verdict: {level, label, color, emoji},
        key_figures: [ {label, value, key} ],
        weakest: pillar|None,         # pilier le plus faible (pour le reproche)
      }
    """
    indicators = score_data.get("indicators", {})

    pillars_out: list[dict[str, Any]] = []
    total = 0.0
    total_weight_available = 0.0

    for p in PILLARS:
        notes = [
            indicators[k]["score"]
            for k in p["keys"]
            if k in indicators and indicators[k].get("score") is not None
        ]
        if notes:
            pillar_score = sum(notes) / len(notes)  # /100
            points = pillar_score / 100 * p["weight"]
            total += points
            total_weight_available += p["weight"]
        else:
            pillar_score = None
            points = None
        n_stars, stars_str = _stars(pillar_score)
        pillars_out.append({
            "key": p["key"],
            "label": p["label"],
            "weight": p["weight"],
            "score": pillar_score,
            "points": points,
            "stars": n_stars,
            "stars_str": stars_str,
            "n": len(notes),
            "hint": p["hint"],
        })

    # Si tous les piliers ne sont pas dispo, on rebase sur 100 pour rester comparable.
    if total_weight_available > 0:
        total_100 = total / total_weight_available * 100
    else:
        total_100 = None

    verdict = _verdict(total_100)

    # ── 5 chiffres clés ──────────────────────────────────────────────
    key_figures: list[dict[str, Any]] = []
    for k in KEY_FIGURE_ORDER:
        cell = indicators.get(k)
        if not cell or cell.get("value") is None:
            continue
        try:
            value_str = cell["fmt"].format(cell["value"])
        except (KeyError, ValueError, TypeError):
            value_str = f"{cell['value']:.2f}"
        key_figures.append({"label": cell.get("label", k), "value": value_str, "key": k})
        if len(key_figures) >= 5:
            break

    scored_pillars = [p for p in pillars_out if p["score"] is not None]
    weakest = min(scored_pillars, key=lambda p: p["score"]) if scored_pillars else None

    return {
        "total": total_100,
        "pillars": pillars_out,
        "verdict": verdict,
        "key_figures": key_figures,
        "weakest": weakest,
    }


def _verdict(total: float | None) -> dict[str, str]:
    """Score élevé = qualité/prix raisonnable = risque faible."""
    if total is None:
        return {"level": "n/a", "label": "DONNÉES INSUFFISANTES",
                "color": "#666666", "emoji": "⚪"}
    if total >= 75:
        return {"level": "low", "label": "LOW-RISK",
                "color": "#00C49A", "emoji": "🟢"}
    if total >= 60:
        return {"level": "medium", "label": "MEDIUM-RISK",
                "color": "#F4C542", "emoji": "🟡"}
    return {"level": "high", "label": "HIGH-RISK",
            "color": "#E74C3C", "emoji": "🔴"}
