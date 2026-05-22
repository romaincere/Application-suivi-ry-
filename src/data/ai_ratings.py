"""Estimation IA des critères qualitatifs (Moat, Management, Market share)
via l'API Anthropic Claude.
"""
from __future__ import annotations

import json

import streamlit as st

SYSTEM_PROMPT = """Tu es un analyste financier expert. Tu évalues des actions cotées sur 3 critères qualitatifs en t'appuyant sur ta connaissance de l'entreprise, son secteur, sa position concurrentielle et les données financières fournies.

Pour CHAQUE critère, attribue une note parmi exactement : 0, 50 ou 100.

1. **moat** (avantage concurrentiel durable)
   - 100 : large moat — barrière à l'entrée structurelle (marque, effets réseau, échelle, switching costs élevés, brevets clés)
   - 50 : moat étroit — avantage modéré ou à durée limitée
   - 0 : aucun moat — produit banalisé, forte concurrence

2. **management_quality** (qualité du management et allocation du capital)
   - 100 : remarquable — track record d'allocation de capital exemplaire, transparence, vision long-terme
   - 50 : fiable — management compétent et sans scandale
   - 0 : décevant — décisions hasardeuses, pertes de confiance, controverses

3. **market_share** (dynamique de parts de marché)
   - 100 : en hausse — gagne du terrain face à la concurrence
   - 50 : stables — maintient sa position
   - 0 : en baisse — perd des parts de marché

Réponds STRICTEMENT en JSON valide, rien d'autre :
{
  "moat": <0|50|100>,
  "management_quality": <0|50|100>,
  "market_share": <0|50|100>,
  "reasoning": "Justification courte (3-5 phrases) en français qui résume ton raisonnement sur les 3 critères."
}
"""


def is_configured() -> bool:
    try:
        return bool(st.secrets["anthropic_api_key"])
    except (KeyError, FileNotFoundError):
        return False


def _summarize_info(info: dict) -> dict:
    keys = [
        "longBusinessSummary", "sector", "industry", "country",
        "marketCap", "trailingPE", "forwardPE", "pegRatio",
        "returnOnEquity", "profitMargins", "revenueGrowth",
        "earningsGrowth", "debtToEquity", "freeCashflow",
    ]
    out: dict = {}
    for k in keys:
        v = info.get(k)
        if v is None:
            continue
        if isinstance(v, str) and len(v) > 800:
            v = v[:800] + "…"
        out[k] = v
    return out


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def get_ai_ratings(ticker: str, name: str, info: dict) -> dict | None:
    """Retourne {moat, management_quality, market_share, reasoning} ou None.

    Cache 7 jours par ticker pour limiter le coût.
    """
    if not is_configured():
        return None
    try:
        import anthropic
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=st.secrets["anthropic_api_key"])
    except Exception:
        return None

    summary = _summarize_info(info)
    user_prompt = (
        f"Action à évaluer :\n"
        f"- Ticker : {ticker}\n"
        f"- Nom : {name}\n"
        f"- Données financières clés :\n"
        f"```json\n{json.dumps(summary, indent=2, ensure_ascii=False)}\n```\n\n"
        f"Donne ta notation au format JSON demandé."
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()
    except Exception:
        return None

    # Robust JSON extraction
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError:
        return None

    # Validate
    out = {}
    for key in ("moat", "management_quality", "market_share"):
        v = data.get(key)
        if v in (0, 50, 100):
            out[key] = int(v)
    if not out:
        return None
    out["reasoning"] = data.get("reasoning", "")
    return out
