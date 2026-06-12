"""Narratif IA du risk score : le reproche majeur + 3 catalyseurs.

S'appuie sur l'API Anthropic Claude si configurée. À défaut, un repli
déterministe dérive le reproche du pilier le plus faible et propose des
catalyseurs génériques fondés sur les indicateurs — clairement signalés
comme heuristiques (pas une recherche).
"""
from __future__ import annotations

import json

import streamlit as st

from src.data.ai_ratings import _summarize_info, is_configured

SYSTEM_PROMPT = """Tu es un analyste actions senior : école Buffett/Munger sur la qualité, école Graham sur la marge de sécurité. On te fournit le risk score déjà calculé d'une action (4 piliers pondérés sur 100) ainsi que ses indicateurs financiers.

Ta mission, en français, STRICTEMENT factuelle :
1. "major_reproach" : LE seul reproche majeur de la thèse (1-2 phrases). Le défaut le plus structurant, pas une liste.
2. "catalysts" : exactement 3 catalyseurs prochains réalistes pouvant faire bouger le score (chacun 1 phrase courte).
3. "verdict_note" : une phrase qui résume le profil de risque.

Règles :
- Ne JAMAIS inventer de chiffres précis (montants, dates de publication, parts de marché exactes). Reste qualitatif ou réfère-toi aux ordres de grandeur fournis.
- Si une donnée manque, raisonne sur ce qui est disponible sans combler par de l'imaginaire.

Réponds STRICTEMENT en JSON valide, rien d'autre :
{
  "major_reproach": "...",
  "catalysts": ["...", "...", "..."],
  "verdict_note": "..."
}
"""


def _fallback(name: str, risk: dict) -> dict:
    """Repli déterministe sans appel API."""
    weakest = risk.get("weakest")
    if weakest:
        reproach = (
            f"Le pilier le plus faible est **{weakest['label']}** "
            f"({weakest['score']:.0f}/100) : c'est là que se concentre le risque "
            f"de la thèse sur {name}."
        )
    else:
        reproach = "Données insuffisantes pour isoler un reproche majeur fiable."
    catalysts = [
        "Prochaine publication de résultats trimestriels (surprise vs consensus).",
        "Évolution des taux / multiples du secteur (impact direct sur la valorisation).",
        "Annonce d'allocation du capital : dividende, rachats d'actions ou M&A.",
    ]
    return {
        "major_reproach": reproach,
        "catalysts": catalysts,
        "verdict_note": "",
        "source": "heuristique (pas d'IA)",
    }


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def get_risk_narrative(ticker: str, name: str, info: dict, risk: dict) -> dict:
    """Retourne {major_reproach, catalysts[3], verdict_note, source}.

    Utilise Claude si une clé Anthropic est configurée, sinon un repli
    heuristique. Cache 7 jours par ticker.
    """
    if not is_configured():
        return _fallback(name, risk)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=st.secrets["anthropic_api_key"])
    except Exception:
        return _fallback(name, risk)

    pillars_summary = {
        p["label"]: (None if p["score"] is None else round(p["score"]))
        for p in risk.get("pillars", [])
    }
    figures = {f["label"]: f["value"] for f in risk.get("key_figures", [])}
    payload = {
        "ticker": ticker,
        "nom": name,
        "score_total_sur_100": (
            None if risk.get("total") is None else round(risk["total"])
        ),
        "verdict": risk.get("verdict", {}).get("label"),
        "piliers_sur_100": pillars_summary,
        "chiffres_cles": figures,
        "fondamentaux": _summarize_info(info),
    }
    user_prompt = (
        "Risk score à commenter :\n"
        f"```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```\n\n"
        "Donne ton analyse au format JSON demandé."
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()
    except Exception:
        return _fallback(name, risk)

    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError:
        return _fallback(name, risk)

    catalysts = data.get("catalysts") or []
    if not isinstance(catalysts, list) or len(catalysts) < 1:
        return _fallback(name, risk)

    return {
        "major_reproach": data.get("major_reproach")
        or _fallback(name, risk)["major_reproach"],
        "catalysts": [str(c) for c in catalysts[:3]],
        "verdict_note": data.get("verdict_note", ""),
        "source": "Claude",
    }
