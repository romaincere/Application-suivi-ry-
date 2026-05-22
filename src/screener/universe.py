"""Listes statiques de tickers pour le screener (univers de référence)."""
from __future__ import annotations

CAC_40 = [
    "AC.PA", "AI.PA", "AIR.PA", "ALO.PA", "BN.PA", "BNP.PA", "CA.PA", "CAP.PA",
    "CS.PA", "DG.PA", "DSY.PA", "EL.PA", "EN.PA", "ENGI.PA", "ERF.PA", "HO.PA",
    "KER.PA", "LR.PA", "MC.PA", "ML.PA", "MT.PA", "OR.PA", "ORA.PA", "PUB.PA",
    "RI.PA", "RMS.PA", "RNO.PA", "SAF.PA", "SAN.PA", "SGO.PA", "STLAP.PA",
    "STMPA.PA", "SU.PA", "SW.PA", "TEP.PA", "TTE.PA", "URW.PA", "VIE.PA",
    "VIV.PA", "WLN.PA",
]

US_MEGA_CAPS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL",
    "JPM", "V", "JNJ", "WMT", "PG", "MA", "XOM", "HD", "CVX", "ABBV", "KO",
    "PEP", "COST", "MRK", "BAC", "ADBE", "CRM", "NFLX", "TMO", "ABT", "ACN",
    "MCD", "CSCO", "AMD", "LIN", "TXN", "DHR", "INTU", "QCOM", "AMGN", "PFE",
    "IBM", "GS", "RTX", "CAT", "HON", "UNH", "DIS", "PM", "LOW", "ELV",
]

NASDAQ_100 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "PEP",
    "COST", "CSCO", "ADBE", "NFLX", "TMUS", "AMD", "INTC", "INTU", "CMCSA",
    "QCOM", "TXN", "HON", "AMGN", "AMAT", "BKNG", "SBUX", "GILD", "ADP",
    "ISRG", "VRTX", "REGN", "MU", "MDLZ", "ADI", "LRCX", "PYPL", "CSX",
    "KLAC", "ASML", "MELI", "MAR", "PANW", "SNPS", "CDNS", "ABNB", "ORLY",
    "FTNT", "CHTR", "ROST", "PCAR", "MNST",
]

UNIVERSES: dict[str, list[str]] = {
    "CAC 40 (France)": CAC_40,
    "US Mega Caps (~50)": US_MEGA_CAPS,
    "Nasdaq 100 (top 50)": NASDAQ_100,
}
