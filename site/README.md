# 🌿 Site web — Berdea Paysage

Site vitrine professionnel pour **Berdea Paysage**, paysagiste à Bayonne
(Pays Basque & Sud des Landes) : création / aménagement de jardins et entretien d'extérieurs.

Site **statique** (HTML / CSS / JavaScript), sans dépendance ni build :
il fonctionne directement dans un navigateur et s'héberge gratuitement.

## 📂 Structure

```
site/
├── index.html          # Page unique (toutes les sections)
├── css/style.css       # Styles & design (palette verte Berdea)
├── js/main.js          # Menu mobile, animations, formulaire
└── assets/img/
    ├── logo.svg        # Logo (arbre dans un cercle)
    └── favicon.svg     # Icône d'onglet
```

## 👀 Voir le site en local

Ouvrez simplement `index.html` dans un navigateur, ou lancez un petit serveur :

```bash
cd site
python3 -m http.server 8000
# puis ouvrez http://localhost:8000
```

## ✏️ À personnaliser

Tout est en clair dans `index.html` :

- **Téléphone / e-mail** : recherchez `contact@berdea-paysage.fr` et le bloc « Contact ».
- **Zones d'intervention** : section `#zone`.
- **Textes des services** : section `#services`.
- **Photos** : la galerie (`#realisations`) utilise des dégradés en attendant de vraies
  photos. Pour ajouter une photo, remplacez une `figure.gallery-item` par une balise
  `<img>` (placez les images dans `assets/img/`).
- **Logo** : remplacez `assets/img/logo.svg` par le logo officiel si vous l'avez en fichier.

### Activer le formulaire de contact

Le formulaire utilise [Formspree](https://formspree.io) (gratuit) :

1. Créez un compte et un formulaire sur Formspree.
2. Copiez l'ID fourni (ex. `xityabcd`).
3. Dans `index.html`, remplacez `your_form_id` dans
   `action="https://formspree.io/f/your_form_id"` par votre ID.

Tant que ce n'est pas fait, le formulaire affiche un message invitant à envoyer un e-mail.

## 🚀 Mettre en ligne (gratuit)

- **Netlify / Vercel** : glissez-déposez le dossier `site/`, ou connectez le dépôt.
- **GitHub Pages** : publiez le dossier `site/` (Settings → Pages).

## 🎨 Identité

- Vert profond `#1b4332`, vert feuille `#3a7d52`, vert clair `#95d5b2`, sable `#f4efe6`.
- Titres : *Fraunces* · Texte : *Inter*.
