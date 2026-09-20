# Elections 2D3D
**Auteur** : Dominique Delaire   
**Date de création** : Juillet 2026   
**Date de modification** : 20 septembre 2026

Génère des visualisations 3D/2D interactives des élections provinciales du Québec à partir des données ouvertes officielles d'Élections Québec (DGEQ) utilisable facilement sous Google Earth et My Google Maps.

Le résultat : les 125 (ou 127 depuis 2026) circonscriptions du Québec **extrudées en 3D** sur Google Earth, colorées par parti gagnant, avec hauteur proportionnelle à la marge de victoire ou au pourcentage. Génère aussi des résultats pour être utilisé sur Google maps, my maps.

## Ce que cela produit

| Fichier généré | Ouverture | Rendu |
|----------------|-----------|-------|
| `quebec_elections_3d.kmz` | Google Earth Pro (Desktop) | 3D immersive complète |
| `quebec_elections_2d.kmz` | Google My Maps, tout SIG | Version 2D allégée (< 5 Mo) |

<img width="2560" height="1440" alt="Screenshot_20260920_143838" src="https://github.com/user-attachments/assets/a7c5933e-ded1-44a2-be5f-acf275b9dc78" />
<img width="2560" height="1440" alt="Screenshot_20260920_140854" src="https://github.com/user-attachments/assets/36028cff-a0ec-48db-b20f-720af007839b" />



## Prérequis

- Python 3.10 ou plus
- Connexion internet (téléchargement automatique des données)
- Environ 50 Mo d'espace disque

## Installation

```bash
# Télécharger les fichiers ou cloner le dépot

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

Contenu de `requirements.txt` :

```
geopandas>=0.14
simplekml>=1.3
pandas>=2.0
requests>=2.31
unidecode>=1.3
```

## Utilisation

### Étape 1 : Générer le fichier complet pour Google Earth Pro

```bash
python3 quebec_elections_3d_pourgoogleearth.py
```

Ce script :

1. Télécharge automatiquement les données officielles du DGEQ dans `data_quebec/`
2. Calcule les résultats par circonscription
3. Génère `quebec_elections_3d.kmz` avec les 2 couches (2D au sol + 3D extrudée) pour Google Earth
**Ouvrir le résultat** : double-clique sur `quebec_elections_3d.kmz` dans Google Earth Pro Desktop, puis incline la vue avec `Ctrl + ↑` pour voir la 3D.

### Étape 2 : Générer la version 2D pour Google My Maps

```bash
python3 quebec_elections_2d_pourgooglemaps.py
```

Ce script réutilise les données déjà téléchargées et produit `quebec_elections_2d.kmz`, une version simplifiée sous 5 Mo compatible avec l'import de Google My Maps.

**Import dans Google My Maps** :

1. `mymaps.google.com` → Créer une nouvelle carte
2. Sur le calque : Importer → glisser `quebec_elections_2d.kmz`

## Configuration

Chaque script contient un bloc `CONFIGURATION` en haut, éditable sans toucher au reste du code.

### Choisir l'élection

Éditer `ELECTION` et `CARTE` dans les deux scripts :

```python
# Élections générales 2022 (par défaut)
ELECTION = "gen2022-10-03"
CARTE = "2022"

# Élections générales 2018
ELECTION = "gen2018-10-01"
CARTE = "2017"

# Élections générales 2014
ELECTION = "gen2014-04-07"
CARTE = "2011"
```

### Configuration spéciale pour les élections du 5 octobre 2026

Les élections générales 2026 utilisent une **structure d'URLs différente** des archives : pendant la période de scrutin, les résultats sont sur un chemin "live" sans préfixe de date, mis à jour toutes les 2 à 5 minutes.

**Pendant la soirée du 5 octobre 2026** (à partir de 20 h HAE) et jusqu'à la publication définitive dans les archives, remplacer le bloc `URLS` dans les scripts par :

```python
CARTE = "2026"

BASE_CARTES = "https://donnees.electionsquebec.qc.ca/autres/provincial"
BASE_LIVE = "https://donnees.electionsquebec.qc.ca/production/provincial/resultats"

URLS = {
    "shapefile": f"{BASE_CARTES}/circonscriptions_electorales_{CARTE}_shapefile.zip",
    "candidats": f"{BASE_LIVE}/candidats.csv",
    "circonscriptions": f"{BASE_LIVE}/circonscriptions.csv",
}
```

**Une fois les données archivées** (généralement quelques jours après le scrutin), la configuration redevient standard :

```python
ELECTION = "gen2026-10-05"
CARTE = "2026"
# Laisser le bloc URLS d'origine
```

**Notes importantes pour 2026** :

- La nouvelle carte électorale 2026 contient **127 circonscriptions** (contre 125 en 2022)
- Les données de résultats sont **inaccessibles entre le 20 septembre 2026 et le 5 octobre 2026 à 20 h**
- Pour rafraîchir automatiquement pendant la soirée électorale, supprimer le CSV téléchargé avant chaque relance :
  ```bash
  rm -f data_quebec/candidats_*.csv && python3 quebec_elections_3d_pourgoogleearth.py
  ```

### Ajuster l'apparence 3D

Dans `quebec_elections_3d_pourgoogleearth.py` et `quebec_elections_2d_pourgooglemaps.py` :

```python
FACTEUR_HAUTEUR = 150        # 50 = discret, 150 = équilibré , 500 = imposant
CRITERE_HAUTEUR = "marge"    # "marge" (recommandé) ou "pourcentage_gagnant"
OPACITE = 180                # 100 = très transparent, 255 = opaque
```

### Ajuster la simplification (version Google Maps uniquement)

Dans `quebec_elections_2d_pourgooglemaps.py` :

```python
TOLERANCE_SIMPLIFICATION = 0.0005   # ~50 m, ~1 Mo (défaut)
# TOLERANCE_SIMPLIFICATION = 0.001  # ~100 m, très léger
# TOLERANCE_SIMPLIFICATION = 0.002  # ~200 m, ultra léger
```

## Couleurs des partis

Modifiables dans le dictionnaire `COULEURS_PARTIS` de chaque script :

| Parti | Code | Couleur par défaut |
|-------|------|--------------------|
| Coalition Avenir Québec | CAQ | `#00A9E0` (bleu ciel) |
| Parti libéral du Québec | PLQ | `#E60000` (rouge) |
| Québec solidaire | QS | `#FF6600` (orange) |
| Parti québécois | PQ | `#003DA5` (bleu foncé) |
| Parti conservateur du Québec | PCQ | `#663399` (violet) |
| Parti vert du Québec | PVQ | `#4CAF50` (vert) |
| Indépendants | IND | `#888888` (gris) |

## Ouvrir les résultats

### Google Earth Pro Desktop (pour la 3D immersive)

Sur Fleurdelix : Google earth est préinstallé.
Sur Linux Ubuntu : 

```bash
wget https://dl.google.com/dl/earth/client/current/google-earth-pro-stable_current_amd64.deb
sudo apt install ./google-earth-pro-stable_current_amd64.deb
```

Sur Windows/macOS : télécharger sur [google.com/earth/versions](https://www.google.com/earth/versions/).

**Google Earth Web n'affiche pas correctement l'extrusion 3D**. Utiliser la version Desktop.

### Google My Maps (pour partager sur le web)

Utiliser la version 2D (`quebec_elections_2d.kmz`) sur [mymaps.google.com](https://mymaps.google.com). Rendu en 2D uniquement (Google My Maps ne gère pas la 3D).

### QGIS ou tout autre SIG

Les deux KMZ s'ouvrent directement dans QGIS, ArcGIS, uMap, etc.
Un exemple ici avec ArcGIS avec le nom des 2 premiers candidats par circonscription:  

<img width="2560" height="1440" alt="Screenshot_20260920_164225" src="https://github.com/user-attachments/assets/00fe2514-1ab4-4ba1-9781-93b8e1383121" />


## Sources des données

Toutes les données proviennent d'**Élections Québec (DGEQ)** en libre accès :

- **Cartes électorales** : [donneesquebec.ca](https://www.donneesquebec.ca) et [dgeq.org](https://www.dgeq.org)
- **Résultats électoraux** : [dgeq.org/donnees.html](https://www.dgeq.org/donnees.html) (en cours) et [dgeq.org/archives.html](https://www.dgeq.org/archives.html) (passées)
- **Documentation** : [dgeq.org/documentation.html](https://www.dgeq.org/documentation.html)

## Structure du projet

```
quebec-elections-3d/
├── quebec_elections_3d_pourgoogleearth.py    # Script principal (KMZ 3D complet)
├── quebec_elections_2d_pourgooglemaps.py     # Script version 2D allégée
├── diagnostic_quebec.py                      # Utilitaire de diagnostic des données
├── requirements.txt
├── README.md
├── LICENSE
└── data_quebec/                              # Créé automatiquement au 1er lancement
    ├── circonscriptions_2022.zip
    ├── circonscriptions_2022/
    ├── candidats_gen2022-10-03.csv
    └── circonscriptions_gen2022-10-03.csv
```

## Dépannage

**Erreur `ModuleNotFoundError` au lancement**  
Activer l'environnement virtuel : `source venv/bin/activate`

**Aucun résultat associé aux circonscriptions**  
La jointure entre le shapefile et les CSV se fait sur les noms de circonscriptions normalisés. Si de nouveaux noms apparaissent (fusion, création, renommage), adapter la fonction `normaliser_nom()`.

**KMZ trop volumineux pour Google My Maps**  
Augmenter `TOLERANCE_SIMPLIFICATION` dans `quebec_elections_2d_pourgooglemaps.py` (voir ci-dessus).

**Google Earth ne montre pas la 3D**  
Vérifier :
- Utilisation de Google Earth **Pro Desktop** (pas Web)
- Case "Bâtiments 3D" cochée dans la barre latérale
- Vue **inclinée** (`Ctrl + ↑`)

## Licence

Code : MIT

Données : sous licence d'utilisation d'Élections Québec (utilisation libre avec mention de la source). Voir [dgeq.org/licence.html](https://www.dgeq.org/licence.html).

## Contribution

Les contributions sont les bienvenues ! Ouvrir une issue pour signaler un bug ou proposer une amélioration.

Possibilités d'évolutions :

- Support des élections fédérales québécoises (Élections Canada)
- Support des élections municipales de Montréal et Québec
- Export animé (comparaison 2018/2022/2026)
- Interface web autonome avec MapLibre
