# Créer un exécutable (Windows, macOS, Linux)

On utilise PyInstaller. Règle d'or : **on construit sur le système cible** —
l'exécutable Windows se fabrique sous Windows, le .app sous macOS, le binaire
Linux sous Linux (idéalement sur la version la plus ancienne que tu veux
supporter).

Dans le dossier du projet, environnement virtuel activé :

```bash
pip install pyinstaller
```

## Windows 11

```bat
pyinstaller --noconfirm --windowed --name FlightBoard --add-data "ui;ui" main.py
```

Résultat : `dist\FlightBoard\FlightBoard.exe` (distribue tout le dossier, ou
zippe-le). `--windowed` évite la console noire derrière la fenêtre.
Pour un fichier unique : ajoute `--onefile` (démarrage un peu plus lent).
Icône : `--icon flightboard.ico`.

## macOS

```bash
pyinstaller --noconfirm --windowed --name FlightBoard --add-data "ui:ui" main.py
```

Résultat : `dist/FlightBoard.app` — glisse-le dans Applications.
(Attention : sur mac/Linux le séparateur de `--add-data` est `:` , sous Windows c'est `;`.)

Premier lancement : macOS peut bloquer l'app car elle n'est pas signée.
Clic droit → Ouvrir → Ouvrir, une seule fois. Pour distribuer proprement à
d'autres personnes il faudrait la signer et la notariser avec un compte
développeur Apple, mais pour ton propre Mac le clic droit suffit.
Icône : `--icon flightboard.icns`.

## Linux (Ubuntu / FleurdeLix OS)

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name FlightBoard --add-data "ui:ui" main.py
```

Résultat : `dist/FlightBoard/FlightBoard`. Particularité Linux : WebKitGTK
n'est PAS embarqué dans l'exécutable — la machine qui exécute doit avoir :

```bash
sudo apt install gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```

Comme le venv a été créé avec `--system-site-packages`, PyInstaller trouvera
`gi` automatiquement.

## Remarques

- Les réglages restent dans le dossier de configuration utilisateur, donc ils
  survivent aux mises à jour de l'exécutable.
- Antivirus Windows : les exécutables PyInstaller `--onefile` déclenchent
  parfois un faux positif ; la variante dossier (sans `--onefile`) passe mieux.
- Pour reconstruire après une modification du code : supprime `build/` et
  `dist/` puis relance la même commande.
