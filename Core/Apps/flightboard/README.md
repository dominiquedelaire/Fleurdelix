# ✈️ FlightBoard

**Afficheur des avions qui passent au-dessus de chez vous**, façon panneau à LED d'aéroport ou scope radar de tour de contrôle.

Application Python multiplateforme (Linux, macOS, Windows 11) construite avec [pywebview](https://pywebview.flowrl.com/). Les données de vol proviennent de réseaux ADS-B communautaires, gratuits et sans clé d'API.

<!-- Ajoutez vos captures d'écran ici :
![Tableau LED](docs/screenshots/tableau-led.png)
![Radar LED](docs/screenshots/radar-led.png)
![Radar lisse](docs/screenshots/radar-lisse.png)
-->

## Fonctionnalités

- **Deux affichages** : tableau texte (compagnie, vol, route, appareil, altitude…) ou radar centré sur votre position, avec balayage animé, avions orientés selon leur cap réel, traînées de trajectoire et mini-indicatifs.
- **Deux rendus** : LED simulées (police matricielle 5×7 dessinée point par point, halo, formes rondes ou carrées) ou lisse, style écran de tour de contrôle (vert phosphore, dégradés, halos lumineux).
- **Informations à la carte** : cochez ce que vous voulez voir — compagnie, numéro de vol, origine → destination, villes, modèle d'avion, immatriculation, altitude, vitesse, distance et direction, cap, taux de montée, compteur. Chaque ligne a sa propre couleur, ou une couleur unique pour tout (préréglages ambre, rouge, vert, blanc).
- **Position** : saisie manuelle des coordonnées, géolocalisation de l'appareil, ou localisation approximative par IP.
- **Réglable** : rayon de recherche (5–250 km), fréquence de rafraîchissement, durée d'affichage par vol, unités métriques ou impériales, taille et forme des LED, couleurs du fond et du radar.
- **Défilement** automatique des textes trop longs, rotation par pages si tout ne tient pas à l'écran.
- **Utilisable comme cadre** : plein écran d'une touche, interface qui s'efface toute seule.
- **iPad / téléphone** : mode serveur pour afficher le tableau sur n'importe quel appareil du réseau local.

## Installation

Prérequis : Python 3.9 ou plus récent.

```bash
git clone https://github.com/<votre-compte>/flightboard.git
cd flightboard
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

### Linux (Ubuntu / Debian)

pywebview s'appuie sur WebKitGTK, à installer via apt **avant** de créer le venv, et le venv doit voir les paquets système :

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
python3 -m venv .venv --system-site-packages
```

Sous Wayland, si la fenêtre reste noire ou scintille :
`WEBKIT_DISABLE_COMPOSITING_MODE=1 python main.py` ou `GDK_BACKEND=x11 python main.py`.

### macOS

Rien de plus : WebKit est intégré au système (`pyobjc` s'installe automatiquement avec pywebview).

### Windows 11

Rien de plus : WebView2 est déjà présent.

## Lancement

```bash
python main.py                 # fenêtre native
python main.py --fullscreen    # plein écran (mode « cadre »)
python main.py --browser       # sans pywebview : serveur local + navigateur
python main.py --host 0.0.0.0  # accessible depuis un iPad/téléphone du réseau local
python main.py --debug         # outils de développement (clic droit → Inspecter)
```

## Raccourcis

| Touche / geste | Action |
|---|---|
| `S` ou bouton ⚙ (survol de la souris) | ouvrir/fermer les réglages |
| `R` | basculer tableau texte ↔ radar |
| `F` | plein écran |
| `→` ou double-toucher (tactile) | vol suivant |
| `Échap` | fermer les réglages |

## Réglages

Tout se règle dans le panneau ⚙ et se prévisualise en direct ; « Enregistrer » conserve les choix.

- **Position** — nom du lieu, latitude/longitude, bouton « Géolocaliser l'appareil » (selon plateforme) ou « Localiser par IP » (ville approximative).
- **Portée et rythme** — rayon de recherche, fréquence de rafraîchissement des données, durée d'affichage de chaque vol, unités.
- **Apparence** — affichage (tableau/radar), rendu (LED simulées/lisse), taille et forme des LED, halo, couleur du fond, des LED éteintes et du radar.
- **Couleurs du texte** — une couleur unique (préréglages inclus) ou une couleur par information.
- **Informations affichées** — cases à cocher, dans l'ordre d'affichage.

Les réglages sont enregistrés dans `settings.json`, hors du dossier du projet :

| Système | Emplacement |
|---|---|
| Linux | `~/.config/FlightBoard/` |
| macOS | `~/Library/Application Support/FlightBoard/` |
| Windows | `%APPDATA%\FlightBoard\` |

## Affichage sur iPad / téléphone

L'application tourne sur un ordinateur du réseau ; l'iPad sert d'écran.

1. Sur l'ordinateur : `python main.py --host 0.0.0.0` — le terminal affiche l'adresse à utiliser (ex. `http://192.168.1.20:8765/`).
2. Sur l'iPad : ouvrir cette adresse dans Safari, puis Partager → « Sur l'écran d'accueil ». Lancée depuis cette icône, l'app s'affiche en plein écran.
3. Un toucher fait apparaître le bouton des réglages, un double-toucher passe au vol suivant.

Pensez à désactiver la mise en veille de l'iPad pour un affichage permanent.

## Créer un exécutable

Voir [build.md](build.md) : instructions PyInstaller détaillées pour Windows (`.exe`), macOS (`.app`) et Linux, avec les pièges à éviter (séparateur `--add-data`, signature macOS, dépendances WebKitGTK, antivirus).

## Sources de données

| Donnée | Service |
|---|---|
| Positions des avions (ADS-B) | [airplanes.live](https://airplanes.live) — repli automatique sur [adsb.lol](https://adsb.lol) |
| Route, compagnie, type d'appareil | [adsbdb.com](https://www.adsbdb.com) |
| Localisation par IP | [ip-api.com](https://ip-api.com) |

Ces services sont gratuits et communautaires : merci de garder un rafraîchissement raisonnable (≥ 10 s) et de ne pas en faire un usage intensif. Les données affichées dépendent de la couverture ADS-B locale ; certains vols n'ont pas de route connue (« Route inconnue ») et les avions privés sont affichés sans nom de propriétaire.

## Structure du projet

```
flightboard/
├── main.py           # lancement : fenêtre native (pywebview) ou serveur local (--browser/--host)
├── backend.py        # réglages, géographie, récupération et enrichissement des vols
├── ui/
│   └── index.html    # toute l'interface : rendu LED et lisse, radar, panneau de réglages
├── requirements.txt
├── build.md          # créer des exécutables avec PyInstaller
├── README.md
└── LICENSE
```

## Dépannage

- **Fenêtre noire au lancement** : les erreurs s'affichent en rouge en bas à gauche de la fenêtre ; `python main.py --debug` donne accès à la console complète. En dernier recours, `--browser` fonctionne partout.
- **`[pywebview] QT cannot be loaded` au démarrage (Linux)** : sans gravité — pywebview essaie Qt puis bascule sur GTK. Pour le faire taire, forcez GTK : `webview.start(gui="gtk")` dans `main.py`.
- **« Données indisponibles »** : les serveurs ADS-B sont peut-être temporairement injoignables, ou votre connexion bloque les requêtes ; réessayez, ou vérifiez avec `curl https://api.airplanes.live/v2/point/45.5/-73.5/20`.
- **Aucun avion détecté** : élargissez le rayon — la couverture varie selon les régions et l'heure.

## Licence

Ce projet est distribué sous licence [MIT](LICENSE).
