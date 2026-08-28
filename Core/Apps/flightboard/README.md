# FlightBoard pour Fleurdelix OS, Linux, Windows, MacOS

**Un Afficheur Temps-réel d'avions qui passent au-dessus de chez vous**, façon panneau à LED d'aéroport ou scope radar de tour de contrôle.

J'ai construit cette application pour l'un de mes enfants, Jad, qui veut être Pilote et qui est fan de flightradar et autres apps. Les écrans vendus dans le commerce qui font exactement la même chose sont vendus plusieurs centaines de dollars.
Ce projet pourrait être intégré sur n'importe quel écran avec par exemple un raspberry PI intégré pour faire la même chose.

C'est une application Python multiplateforme (Fleurdelix OS, Linux, macOS, Windows 11) construite avec [pywebview](https://pywebview.flowrl.com/) et peux s'exécuter aussi sur une tablette ipad , samsung, téléphones, xbox ou TV via navigateur internet.   

Elle est préinstallée sur Fleurdelix OS.   

**Les données de vol proviennent de réseaux ADS-B communautaires, gratuits et sans clé d'API.**

Vue Radar (Lisse non led).  
<img width="2016" height="925" alt="Vue Radar (Lisse non Led)" src="https://github.com/user-attachments/assets/b1b14898-a35e-481e-9adf-ee821ff2252b" />
Vue Texte (Mode Led).  
<img width="2035" height="1051" alt="Vue Texte (Mode Led)" src="https://github.com/user-attachments/assets/88dd2c53-2fb8-4583-b4cc-9f894c9085a7" />
Vue Texte (Non Led).  
<img width="2016" height="1063" alt="Vue Texte (non Led)" src="https://github.com/user-attachments/assets/579025af-92a1-4483-9957-0cb9400be10d" />
Vue Radar (Mode Led).   
<img width="2035" height="1051" alt="Vue Radar (Mode Led)" src="https://github.com/user-attachments/assets/324968eb-a840-432f-b74a-5c625a804fae" />
Exemple de paramètres.  
<img width="404" height="359" alt="Exemple de paramètres de l'application" src="https://github.com/user-attachments/assets/df2ae87a-12b9-4e02-9f38-54ad7b7938e6" />
Lancement sur Ipad depuis App locale.  
<img width="1086" height="1449" alt="testaccesipad2" src="https://github.com/user-attachments/assets/823c05b2-1624-469a-89a6-17e178fbbaea" />
<img width="1086" height="1448" alt="testaccesipad1" src="https://github.com/user-attachments/assets/4fcd707b-0375-4d0e-a052-145be834a747" />



## Fonctionnalités

- **Deux affichages** : tableau texte (compagnie, vol, route, appareil, altitude…) ou radar centré sur votre position, avec balayage animé, avions orientés selon leur cap réel, traînées de trajectoire et mini-indicatifs.
- **Deux rendus** : LED simulées (police matricielle 5×7 dessinée point par point, halo, formes rondes ou carrées) ou lisse, style écran de tour de contrôle (vert phosphore, dégradés, halos lumineux).
- **Informations à la carte** : cochez ce que vous voulez voir : compagnie, numéro de vol, origine & destination, villes, modèle d'avion, immatriculation, altitude, vitesse, distance et direction, cap, taux de montée, compteur. Chaque ligne a sa propre couleur, ou une couleur unique pour tout (préréglages ambre, rouge, vert, blanc).
- **Position** : saisie manuelle des coordonnées, géolocalisation de l'appareil, ou localisation approximative par IP.
- **Réglable** : rayon de recherche (5–250 km), fréquence de rafraîchissement, durée d'affichage par vol, unités métriques ou impériales, taille et forme des LED, couleurs du fond et du radar.
- **Défilement** automatique des textes trop longs, rotation par pages si tout ne tient pas à l'écran.
- **Utilisable comme cadre** : plein écran d'une touche, interface qui s'efface toute seule.
- **iPad / téléphone** : mode serveur pour afficher le tableau sur n'importe quel appareil du réseau local.

Voir la démonstration sur youtube.  
[![Voir la démonstration](https://img.youtube.com/vi/_W8mwUjzd2U/maxresdefault.jpg)](https://www.youtube.com/watch?v=_W8mwUjzd2U)

## Installation

Prérequis : Python 3.9 ou plus récent.

Télécharger les fichiers de flightboard et du sous répertoire ui et copier dans un répertoire en local sur votre ordinateur.

ou cloner le git avec git clone https://github.com/dominiquedelaire/Fleurdelix.git et aller dans le répertoire flightboard dans votre terminal Fleurdelix, linux, mac ou windows.   

```bash
cd flightboard
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

### Fleurdelix OS ou Linux (Ubuntu / Debian)

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

- **Position** : nom du lieu, latitude/longitude, bouton « Géolocaliser l'appareil » (selon plateforme) ou « Localiser par IP » (ville approximative).
- **Portée et rythme** : rayon de recherche, fréquence de rafraîchissement des données, durée d'affichage de chaque vol, unités.
- **Apparence** : affichage (tableau/radar), rendu (LED simulées/lisse), taille et forme des LED, halo, couleur du fond, des LED éteintes et du radar.
- **Couleurs du texte** : une couleur unique (préréglages inclus) ou une couleur par information.
- **Informations affichées** : cases à cocher, dans l'ordre d'affichage.

<img width="404" height="971" alt="Paramètres de l'application" src="https://github.com/user-attachments/assets/65f60d35-5d92-458e-a52b-2ccd31248519" />
<img width="404" height="969" alt="Paramètres de l'application suite" src="https://github.com/user-attachments/assets/44556aec-f8fa-4d29-bc84-3bb7113a7ad4" />


Les réglages sont enregistrés dans `settings.json`, hors du dossier du projet :

| Système | Emplacement |
|---|---|
| Fleurdelix OS / Linux | `~/.config/FlightBoard/` |
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
- **`[pywebview] QT cannot be loaded` au démarrage (Linux)** : sans gravité, pywebview essaie Qt puis bascule sur GTK. Pour le faire taire, forcez GTK : `webview.start(gui="gtk")` dans `main.py`.
- **« Données indisponibles »** : les serveurs ADS-B sont peut-être temporairement injoignables, ou votre connexion bloque les requêtes ; réessayez, ou vérifiez avec `curl https://api.airplanes.live/v2/point/45.5/-73.5/20`.
- **Aucun avion détecté** : élargissez le rayon, la couverture varie selon les régions et l'heure.

## Licence

Ce projet est distribué sous licence [MIT](LICENSE).
