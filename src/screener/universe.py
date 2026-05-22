"""Listes statiques de tickers : univers PEA-éligibles (UE/EEE)."""
from __future__ import annotations

# ── France (Euronext Paris) ────────────────────────────────────────
CAC_40 = [
    "AC.PA", "AI.PA", "AIR.PA", "ALO.PA", "BN.PA", "BNP.PA", "CA.PA", "CAP.PA",
    "CS.PA", "DG.PA", "DSY.PA", "EL.PA", "EN.PA", "ENGI.PA", "ERF.PA", "HO.PA",
    "KER.PA", "LR.PA", "MC.PA", "ML.PA", "MT.PA", "OR.PA", "ORA.PA", "PUB.PA",
    "RI.PA", "RMS.PA", "RNO.PA", "SAF.PA", "SAN.PA", "SGO.PA", "STLAP.PA",
    "STMPA.PA", "SU.PA", "SW.PA", "TEP.PA", "TTE.PA", "URW.PA", "VIE.PA",
    "VIV.PA", "WLN.PA",
]

SBF_120_EXTRA = [  # actions du SBF 120 hors CAC 40
    "ALD.PA", "AKE.PA", "AMUN.PA", "ATO.PA", "BB.PA", "BIM.PA", "BVI.PA",
    "CGG.PA", "CO.PA", "DEC.PA", "EDF.PA", "ELIS.PA", "FDJ.PA", "FR.PA",
    "GET.PA", "GFC.PA", "GLE.PA", "ICAD.PA", "IPN.PA", "IPS.PA", "JCQ.PA",
    "LI.PA", "NEX.PA", "NK.PA", "RCO.PA", "RXL.PA", "SAB.PA", "SCR.PA",
    "SESG.PA", "SOI.PA", "SOP.PA", "SPIE.PA", "UBI.PA", "EDEN.PA", "ETL.PA",
    "ARG.PA", "MAU.PA",
]

# ── Allemagne (Xetra/Frankfurt) ─────────────────────────────────────
DAX_40 = [
    "ADS.DE", "AIR.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE", "BNR.DE",
    "CBK.DE", "CON.DE", "1COV.DE", "DBK.DE", "DB1.DE", "DHL.DE", "DTE.DE",
    "DTG.DE", "ENR.DE", "EOAN.DE", "FRE.DE", "HEI.DE", "HEN3.DE", "HFG.DE",
    "HNR1.DE", "IFX.DE", "MBG.DE", "MRK.DE", "MTX.DE", "MUV2.DE", "P911.DE",
    "PAH3.DE", "PUM.DE", "QIA.DE", "RHM.DE", "RWE.DE", "SAP.DE", "SHL.DE",
    "SIE.DE", "SY1.DE", "VOW3.DE", "VNA.DE", "ZAL.DE",
]

# ── Pays-Bas (Euronext Amsterdam) ───────────────────────────────────
AEX_25 = [
    "ADYEN.AS", "AGN.AS", "AKZA.AS", "ASML.AS", "ASMI.AS", "ASRNL.AS",
    "BESI.AS", "DSFIR.AS", "EXO.AS", "HEIA.AS", "IMCD.AS", "INGA.AS",
    "KPN.AS", "MT.AS", "NN.AS", "PHIA.AS", "PRX.AS", "RAND.AS", "REN.AS",
    "SHELL.AS", "UNA.AS", "UMG.AS", "WKL.AS",
]

# ── Belgique (Euronext Bruxelles) ───────────────────────────────────
BEL_20 = [
    "ABI.BR", "ACKB.BR", "AGS.BR", "ARGX.BR", "AZE.BR", "COFB.BR", "ELI.BR",
    "GBLB.BR", "KBC.BR", "PROX.BR", "SOF.BR", "SOLB.BR", "UCB.BR", "UMI.BR",
    "WDP.BR",
]

UNIVERSES: dict[str, list[str]] = {
    "🇫🇷 CAC 40": CAC_40,
    "🇫🇷 SBF 120 extra": SBF_120_EXTRA,
    "🇩🇪 DAX 40": DAX_40,
    "🇳🇱 AEX 25": AEX_25,
    "🇧🇪 BEL 20": BEL_20,
    "🇪🇺 Tous PEA (CAC + SBF + DAX + AEX + BEL)":
        CAC_40 + SBF_120_EXTRA + DAX_40 + AEX_25 + BEL_20,
}
