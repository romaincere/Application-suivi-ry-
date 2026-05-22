# 📈 Application de suivi de portefeuille & screener d'actions

Application Streamlit pour suivre son portefeuille boursier (actions US, Europe, ETF)
et identifier des opportunités via un screener fondamental + technique.

> **État actuel : Phase 1 — squelette fonctionnel.** L'app se lance, l'auth marche,
> la navigation est en place ; les pages métier seront remplies en Phases 2-4.

## ✨ Stack

- **UI** : [Streamlit](https://streamlit.io) (responsive mobile/tablette out-of-the-box)
- **Données marché** : [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance, gratuit)
- **Persistance** : JSON chiffré (Fernet) versionné dans le repo
- **Auth** : mot de passe simple via `st.secrets`
- **Hébergement cible** : [Streamlit Community Cloud](https://share.streamlit.io) (gratuit)

## 📂 Structure

```
.
├── app.py                      # Entrée Streamlit (auth + navigation)
├── requirements.txt
├── .streamlit/
│   ├── config.toml             # Thème sombre + meta PWA
│   └── secrets.toml.example    # Modèle des secrets (à copier en secrets.toml)
├── data/
│   └── portfolio.enc           # Portefeuille chiffré (créé au 1er enregistrement)
└── src/
    ├── auth/password.py        # Gate par mot de passe
    ├── data/market.py          # Wrapper yfinance + cache
    ├── storage/portfolio_store.py  # Chiffrement Fernet + I/O
    └── ui/
        ├── portfolio_page.py   # Page Portefeuille (Phase 2)
        ├── stock_detail_page.py # Page Détail action (Phase 3)
        └── screener_page.py    # Page Screener (Phase 4)
```

## 🚀 Lancer l'app en local

### 1. Prérequis

- Python 3.11+
- `pip` ou `uv`

### 2. Installation

```bash
git clone https://github.com/romaincere/application-suivi-ry-.git
cd application-suivi-ry-
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

### 3. Configurer les secrets

Génère une clé Fernet :

```bash
python -m src.storage.portfolio_store
```

Copie l'exemple et colle ta clé :

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# édite .streamlit/secrets.toml et renseigne app_password + fernet_key
```

### 4. Lancer

```bash
streamlit run app.py
```

→ ouvre `http://localhost:8501`.

## ☁️ Déployer sur Streamlit Cloud (gratuit)

L'app sera ensuite accessible depuis n'importe quel navigateur, **y compris ton
iPhone et ton iPad**, via une URL publique du type
`https://<nom>.streamlit.app`.

1. **Pousse ce repo sur GitHub** (déjà fait si tu lis ceci depuis GitHub).
2. Va sur [share.streamlit.io](https://share.streamlit.io) et connecte-toi
   avec ton compte GitHub.
3. Clique **"New app"**, sélectionne :
   - Repository : `romaincere/application-suivi-ry-`
   - Branch : `main` (ou celle que tu déploies)
   - Main file path : `app.py`
4. Avant de cliquer **Deploy**, va dans **Advanced settings → Secrets**
   et colle :

   ```toml
   app_password = "ton-mot-de-passe-secret"
   fernet_key = "ta-cle-fernet-generee"
   ```

5. Clique **Deploy**. Au bout d'≈2 minutes, ton URL publique est prête.

> ⚠️ **Important** : la clé Fernet ne doit **jamais** être commitée dans le repo.
> Elle reste exclusivement dans les Secrets de Streamlit Cloud.

À chaque `git push` sur la branche déployée, Streamlit Cloud redéploie
automatiquement la nouvelle version.

## 📱 Ajouter l'app à l'écran d'accueil iPhone/iPad

1. Ouvre ton URL Streamlit (`https://<nom>.streamlit.app`) **dans Safari** (pas Chrome).
2. Tape sur l'icône **Partager** (carré avec une flèche vers le haut).
3. Fais défiler et choisis **"Sur l'écran d'accueil"**.
4. Renomme l'icône (par défaut "Portefeuille") et valide.

L'app apparaît comme une vraie app native, plein écran, dans le dock iOS.

## 🗺️ Roadmap

- [x] **Phase 1** — Squelette : auth, navigation, structure, déploiement
- [ ] **Phase 2** — Portefeuille : saisie positions, P&L, répartition, KPIs
- [ ] **Phase 3** — Détail action : graphiques de cours, indicateurs clés
- [ ] **Phase 4** — Screener : filtres fondamentaux + techniques
- [ ] **Phase 5** — Polish : alertes, exports, perfs

## 🔐 Modèle de sécurité

- L'app est protégée par un mot de passe (`st.secrets["app_password"]`).
- Le portefeuille est sérialisé en JSON puis **chiffré avec Fernet** (AES-128-CBC + HMAC)
  avant d'être écrit dans `data/portfolio.enc`. Ce fichier peut être versionné
  publiquement sans révéler son contenu.
- La clé Fernet n'est **jamais** dans le repo : uniquement dans les Secrets Streamlit Cloud
  ou dans `.streamlit/secrets.toml` en local (ignoré par git).
