# Task365

**Auteur** : Dominique Delaire, Licence MIT, 2026.  



**Assistant personnel local et hors-ligne** : tâches, journal de bord, budget
multi-comptes, contacts, et un module pour travailleurs autonomes avec calcul de
taxes. Tout est stocké dans une base SQLite sur votre machine, **aucune donnée
ne quitte votre ordinateur**.

<img width="614" height="375" alt="screen1" src="https://github.com/user-attachments/assets/af10856b-3e8b-4007-880c-b01445e5b308" />

Task365 propose plusieurs interfaces qui partagent **exactement la même logique et
la même base de données** :

| Commande | Interface |
|---|---|
| `task365 web` | Fenêtre de bureau (HTML/CSS), **recommandée** |
| `task365 <commande>` | Ligne de commande (terminal) |
| `task365 tui` | Interface interactive dans le terminal |
| `task365 gui` | Fenêtre de bureau alternative (DearPyGui) |

---

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Installation](#installation)
- [L'interface de bureau (`task365 web`)](#linterface-de-bureau-task365-web)
  - [Jour](#écran-jour)
  - [Récapitulatif année](#écran-récapitulatif-année)
  - [Récurrences](#écran-récurrences)
  - [Budget](#écran-budget)
  - [Contacts et notes](#écran-contacts-et-notes)
  - [Gestion revenu et dépense](#écran-gestion-revenu-et-dépense)
  - [Catégories](#écran-catégories)
  - [Taxes](#écran-taxes)
- [Référence de la ligne de commande](#référence-de-la-ligne-de-commande)
- [Où sont stockées les données ?](#où-sont-stockées-les-données-)
- [Arborescence du dépôt](#arborescence-du-dépôt)
- [Licence](#licence)

---

## Fonctionnalités

- **Jour** : vue quotidienne rassemblant tâches, journal, sport, alimentation et soldes.
- **Tâches** : drapeau *prioritaire*, tags, récurrences, navigation jour par jour.
- **Journal de bord** : texte libre + métriques chiffrées (humeur, poids, sommeil,
  tension, fréquence cardiaque… et toute métrique personnalisée).
- **Récurrences** : de tâches **ou** d'opérations de budget, quotidiennes,
  hebdomadaires ou mensuelles, avec génération à l'avance.
- **Récapitulatif année** : graphe d'activité annuel + courbes de suivi du poids
  et du sommeil.
- **Budget personnel** : comptes multiples, opérations, virements, soldes à une
  date donnée, répartition par catégorie, **rapprochement bancaire**.
- **Contacts et notes** : carnet simple avec notes rattachées.
- **Module Travailleur autonome** : revenus et dépenses, calcul de taxes
  bidirectionnel, taxes perçues vs payées, exports Excel et CSV.
- **Tags transversaux** : toutes les données peuvent être reliées par des tags.

---

## Installation

Task365 requiert **Python 3.10 ou plus**. La méthode recommandée est
[`pipx`](https://pipx.pypa.io/), qui installe l'application dans un
environnement isolé tout en rendant la commande `task365` disponible partout.

### Linux (Ubuntu / Fleurdelix OS)

```bash
# pipx si absent
sudo apt install pipx
pipx ensurepath      # puis fermer/rouvrir le terminal

# depuis le dossier du projet (celui qui contient pyproject.toml)
pipx install ".[web,export]"
```

### macOS

Sur macOS, `pywebview` utilise **WebKit** (natif) et n'a pas besoin de Qt.
Installation allégée recommandée :

```bash
brew install pipx
pipx ensurepath      # puis fermer/rouvrir le terminal

pipx install ".[export]"
pipx inject task365 pywebview
```

### Windows 11

Installez d'abord **Python 3.10 ou plus** depuis le [site officiel](https://www.python.org/downloads/)
ou via le Microsoft Store. À l'installation depuis le site officiel, cochez
impérativement la case **« Add python.exe to PATH »** sur le premier écran, sinon
les commandes ne seront pas reconnues.

Ouvrez ensuite **PowerShell** (ou l'Invite de commandes) :

```powershell
# installer pipx
py -m pip install --user pipx
py -m pipx ensurepath
```

Fermez puis rouvrez PowerShell pour que le PATH soit pris en compte, placez-vous
dans le dossier du projet (celui qui contient `pyproject.toml`) et installez :

```powershell
cd C:\chemin\vers\Task365
pipx install ".[web,export]"
```

Lancez ensuite l'application :

```powershell
task365 web
```

Sur Windows, `pywebview` utilise **WebView2** (le moteur de rendu d'Edge), en
principe déjà présent sur Windows 11. Si le lancement échoue en signalant
WebView2, installez le [WebView2 Runtime de Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/)
puis relancez.

La base de données se trouve dans votre dossier utilisateur :

```
C:\Users\<VotreNom>\.task365\task365.db
```

Pour y accéder rapidement dans l'Explorateur, tapez `%USERPROFILE%\.task365` dans
la barre d'adresse.

### Groupes de dépendances disponibles

| Extra | Contenu | Utilité |
|---|---|---|
| *(aucun)* | `rich`, `textual` | CLI + TUI seulement |
| `web` | `pywebview`, `qtpy`, `pyside6` | Interface de bureau (Linux/Windows) |
| `export` | `openpyxl` | Export Excel `.xlsx` (le CSV ne demande rien) |
| `gui` | `dearpygui` | Interface de bureau alternative |
| `all` | tout ce qui précède | Installation complète |

### Alternative : environnement virtuel classique

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -e ".[web,export]"
```

Le mode `-e` (éditable) permet de modifier le code source et de voir les
changements au relancement, sans réinstaller.

---

## L'interface de bureau (`task365 web`)

```bash
task365 web
```

La fenêtre s'organise en une **barre latérale** (repliable via ☰) regroupant les
écrans par thème, et une **zone de contenu** à droite. Des badges affichent le
nombre de tâches à faire, de contacts et de récurrences actives.

<img width="1289" height="758" alt="screen1" src="https://github.com/user-attachments/assets/af10856b-3e8b-4007-880c-b01445e5b308" />

<img width="896" height="597" alt="screen3" src="https://github.com/user-attachments/assets/5e4e5254-8886-4d84-bcc8-ca23a7d022dd" />


<!-- Capture d'écran : vue générale -->

### Écran Jour

Le tableau de bord quotidien. Une barre de navigation en haut permet de reculer
(`‹ -1j`), revenir à `Aujourd'hui`, avancer (`+1j ›`), ou sauter à une date
précise via le sélecteur « aller au ».

**Panneau Tâches** : liste des tâches du jour. Chaque ligne comporte :

- une **pastille de priorité** à gauche (pleine et rouge si prioritaire),
  cliquable pour basculer la priorité directement, sans ouvrir de formulaire ;
- une **case à cocher** pour marquer la tâche comme faite ;
- les **tags** associés ;
- les icônes ✎ (modifier) et 🗑 (supprimer).

Le tri est automatique : les tâches **à faire** en haut (prioritaires d'abord),
les tâches **faites** en bas. Cocher une tâche la fait descendre immédiatement.

Le bouton `+ ajouter` ouvre un formulaire avec intitulé, date, tags, case
« prioritaire », et une section **récurrence** (fréquence + intervalle) qui
transforme la saisie en tâche récurrente.

**Panneau Journal** : texte libre accompagné de métriques chiffrées. Des champs
prédéfinis existent (humeur, poids, sommeil, tension, fréquence cardiaque), et
le bouton d'ajout de ligne permet d'enregistrer **n'importe quelle métrique
personnalisée** (nom + valeur). Les métriques `poids` et `sommeil` alimentent
automatiquement les courbes de l'écran Récapitulatif année.

**Panneau Sport** : activité, durée, distance, calories, fréquence cardiaque,
ressenti d'effort et note libre.

**Panneau Alimentation** : libellé, quantité descriptive, calories, protéines,
glucides, lipides saturés et insaturés, fibres, et repas (petit-déj, midi,
soir, collation). Un total nutritionnel du jour est calculé automatiquement.

**Colonne de droite, Comptes & soldes** : solde de chaque compte **à la date
affichée**, avec le total. Naviguer vers une date future montre donc le solde
projeté (en tenant compte des opérations déjà générées).

<!-- Capture d'écran : écran Jour -->

### Écran Récapitulatif année

**Graphe d'activité annuel** : une grille façon « contributions » couvrant une
année glissante, où chaque case représente un jour et son intensité de couleur
le volume d'activité. Un filtre permet de choisir le type d'entrée compté
(tâches, journal, sport…).

**Suivi du poids** : courbe d'évolution sur l'année, avec aire colorée,
graduations, et statistiques en titre : dernière valeur, minimum, maximum,
moyenne et nombre de mesures. Chaque point affiche sa date et sa valeur au survol.

**Suivi du sommeil** : même principe pour les heures de sommeil.

> Les courbes se construisent à partir des métriques `poids` et `sommeil` saisies
> dans le Journal. Il faut au moins deux mesures pour qu'une courbe s'affiche.

<img width="752" height="661" alt="screen4" src="https://github.com/user-attachments/assets/136c15bd-0a6b-45b4-9964-ec515ddcddb0" />

<!-- Capture d'écran : Récapitulatif année -->

### Écran Récurrences

Liste de toutes les récurrences avec, pour chacune : intitulé, **type**
(tâche ou budget), **montant** (pour les récurrences de budget uniquement, coloré
selon dépense/revenu, avec le compte concerné), fréquence, date de début,
dernière génération, tags, et état (actif/inactif).

**Bouton `+ récurrence`** : formulaire de création. Un sélecteur choisit le type :

- **Tâche** : intitulé, fréquence, intervalle, date de début, tags.
- **Opération budget** : ajoute le choix du **compte**, le **montant**, et une
  case « dépense » (cochée par défaut) qui met le montant en négatif.

**Bouton `⏩ Générer à l'avance`** : génère toutes les occurrences dues jusqu'à
une date choisie. Utile pour projeter son solde sur les mois à venir. L'opération
est **idempotente** : relancer ne crée jamais de doublons.

Chaque ligne peut être désactivée/réactivée ou supprimée.

<!-- Capture d'écran : Récurrences -->
<img width="952" height="546" alt="screen5" src="https://github.com/user-attachments/assets/f30066ad-0a8c-465f-b1ef-42c8ea6711db" />


### Écran Budget

**Barre de filtre** : période (du / au), compte, catégorie, plus un raccourci
« Trimestre courant ». Une ligne de résumé indique la période appliquée, le
nombre d'opérations et leur somme.

**Tableau des opérations** : date, libellé, catégorie, montant (vert si positif,
rouge si négatif), et une colonne **« Rappr. »** avec une case à cocher pour le
**rapprochement bancaire**. Cocher une case enregistre immédiatement, sans passer
par le formulaire de modification, pratique pour pointer un relevé bancaire.
Les opérations sont triées de la plus récente à la plus ancienne.

**Boutons `+ opération` et `+ virement`** : la première crée une opération simple
(compte, montant, libellé, date, catégorie, case « dépense ») ; la seconde crée un
**virement entre deux comptes**, enregistré comme deux opérations liées.

**Colonne de droite, Comptes** : solde de chaque compte et total, avec un bouton
`+ compte` pour en créer un nouveau (nom, solde initial, date du solde).

**Colonne de droite, Par catégorie** : total par catégorie sur la période
filtrée, suivi d'une ligne **« Total (revenus − dépenses) »** donnant le solde
net de la période.

<!-- Capture d'écran : Budget -->

### Écran Contacts et notes

Liste des contacts avec leurs tags. Sélectionner un contact affiche ses
informations et ses **notes** rattachées, avec possibilité d'en ajouter, d'en
modifier ou d'en supprimer. Les contacts eux-mêmes sont créables, modifiables et
supprimables.

<!-- Capture d'écran : Contacts -->

### Écran Gestion revenu et dépense

Le cœur du **module Travailleur autonome**.

**Boutons `+ dépense` et `+ revenu`** : ouvrent le même formulaire, pré-réglé sur
le type choisi. Le formulaire contient :

- un sélecteur **Dépense / Revenu** ;
- la **date** et la **description** ;
- le **tiers**, dont le libellé s'adapte automatiquement : « Fournisseur » pour
  une dépense, « Client » pour un revenu ;
- la **catégorie** et le **code de taxe** ;
- une case **« pas de taxes »** ;
- une case **« compte perso »** (cochée par défaut) ; décochée, l'opération est
  marquée comme compte d'entreprise ;
- les montants **HT / TPS / TVQ / TTC** avec **calcul bidirectionnel** : saisir le
  HT calcule le TTC, saisir le TTC recalcule le HT ;
- le **pourboire**, la **devise**, et un montant en devise étrangère optionnel.

**Barre de filtre** : période, type (revenus / dépenses / les deux), catégorie,
raccourci « Trimestre courant », et boutons d'export **Excel** et **CSV**.

**Tableau** : date, type (revenu en vert, dépense en rouge), description, tiers,
catégorie, code de taxe, compte (perso/entreprise), HT, taxes, TTC, pourboire,
total payé. Trois actions par ligne :

| Icône | Action |
|---|---|
| ✎ | Modifier l'opération |
| ⧉ | **Dupliquer** : pré-remplit le formulaire avec toutes les valeurs, date remise à aujourd'hui, en mode création (l'originale reste intacte) |
| 🗑 | Supprimer |

**Récapitulatif** : trois blocs en bas :

1. **Revenus (taxes perçues)** : total HT, détail par taxe (TPS, TVQ…), total des
   taxes perçues, total TTC.
2. **Dépenses (taxes payées)** : mêmes lignes pour les dépenses, plus les pourboires.
3. **Taxes nettes à remettre (perçues − payées)** : le montant à remettre à Revenu
   Québec / l'ARC. Un solde négatif indique un crédit en votre faveur.

**Exports** : le fichier généré (Excel ou CSV) reprend la période et les filtres
affichés, avec une colonne par type de taxe et une ligne de totaux. Une boîte de
dialogue native permet de choisir l'emplacement. Le CSV est encodé en UTF-8 avec
BOM et séparé par des points-virgules, pour s'ouvrir correctement dans Excel,
OnlyOffice et LibreOffice.

<!-- Capture d'écran : Gestion revenu et dépense -->

### Écran Catégories

Gestion simple des catégories de dépenses et revenus : création, renommage,
suppression.

<!-- Capture d'écran : Catégories -->

### Écran Taxes

Gestion des **codes de taxe**. Un code regroupe une ou plusieurs lignes de taxe
(nom + taux en pourcentage). Le code **Québec** (TPS 5 % + TVQ 9,975 %) est créé
automatiquement au premier lancement et défini par défaut.

Il est possible de créer d'autres codes (TVA, taxes d'autres provinces, taux
historiques…), de les modifier, d'en changer le code par défaut et de les
supprimer. Le calcul de taxes du module travailleur autonome s'appuie sur ces
définitions.

<!-- Capture d'écran : Taxes -->

---

## Référence de la ligne de commande

Aide générale :

```bash
task365 --help
task365 <commande> --help
```

### Formats de date acceptés

Partout où une date est demandée, ces formes sont comprises :

| Forme | Signification |
|---|---|
| `today`, `auj`, `aujourdhui` | aujourd'hui |
| `tomorrow`, `demain` | demain |
| `yesterday`, `hier` | hier |
| `+3` ou `+3d` | dans 3 jours |
| `-2` | il y a 2 jours |
| `2026-06-10` | date ISO |
| `10/06/2026`, `10-06-2026` | date française |
| `10/06` | jour/mois, année courante |

### `task` : tâches

```bash
task365 task add <titre> [--due DATE] [--tags TAGS] [--metric CLÉ=VALEUR]
task365 task list [--tag TAG] [--done] [--todo]
task365 task done <id>
task365 task edit <id> [--title TITRE] [--due DATE] [--tags TAGS] [--done|--todo]
task365 task rm <id>
```

`--metric` peut être répété (ex : `-m budget=200`). `--tags` **remplace**
l'ensemble des tags lors d'une modification.

```bash
task365 task add "Appeler le notaire" --due tomorrow --tags admin
task365 task list --todo
```

### `journal` : journal de bord

```bash
task365 journal add <texte> [--mood 0-10] [--date DATE] [--tags TAGS] [--metric CLÉ=VALEUR]
task365 journal list [--tag TAG] [--limit N]
task365 journal edit <id> [--text TEXTE] [--mood N] [--date DATE] [--tags TAGS] [--metric CLÉ=VALEUR]
task365 journal rm <id>
```

Les métriques acceptent une unité optionnelle après `:`,
par exemple `-m sommeil=7:h` ou `-m poids=78.5`.

```bash
task365 journal add "Bonne journée" --mood 8 -m poids=78.5 -m sommeil=7:h
```

### `contact` : carnet de contacts

```bash
task365 contact add <nom> [--info INFOS] [--tags TAGS]
task365 contact list [--tag TAG]
task365 contact note <id> <texte>
task365 contact show <id>
```

### `recur` : récurrences

```bash
task365 recur add <titre> --freq daily|weekly|monthly [--interval N]
                          [--start DATE] [--until DATE] [--tags TAGS]
                          [--type TYPE] [--account COMPTE] [--amount MONTANT]
task365 recur list [--all]
task365 recur run [--until DATE]
task365 recur toggle <id> on|off
task365 recur rm <id>
```

Pour une récurrence de **budget**, indiquer `--account` (id ou nom) et `--amount`
(montant signé, négatif = dépense). Préciser `--account` bascule automatiquement
le type en `budget`, donc `--type budget` est facultatif.

`recur run --until` génère les occurrences **à l'avance** jusqu'à la date
indiquée ; l'opération est idempotente et ne crée jamais de doublons.

```bash
task365 recur add "Loyer" --freq monthly --start 2026-01-01 \
                 --account Courant --amount -1200
task365 recur run --until 2026-12-31
```

### `account` : comptes bancaires

```bash
task365 account add <nom> [--balance SOLDE] [--opened DATE]
task365 account list [--date DATE]
task365 account edit <compte> [--name NOM] [--balance SOLDE] [--opened DATE]
task365 account rm <compte>
```

`<compte>` accepte un **id ou un nom**. `account list --date` affiche les soldes
à une date donnée.

### `budget` : opérations et soldes

```bash
task365 budget add <compte> <montant> <libellé> [--date DATE] [--tags TAGS] [--expense]
task365 budget transfer <source> <destination> <montant> [--label LIBELLÉ] [--date DATE] [--tags TAGS]
task365 budget list [--account COMPTE] [--since DATE] [--until DATE] [--tag TAG]
task365 budget balance <compte> [--date DATE] [--history] [--since DATE]
task365 budget categories [--account COMPTE] [--since DATE] [--until DATE]
task365 budget edit <id> [--amount M] [--label L] [--date D] [--account A] [--tags T] [--expense]
task365 budget rm <id>
task365 budget recalc
```

Le montant est **signé** : négatif = dépense. L'option `--expense` force le
montant en négatif. `budget rm` sur un virement supprime **les deux jambes**.

```bash
task365 budget add Courant -45.50 "Épicerie" --tags alimentation
task365 budget transfer Courant Épargne 500 --label "Mise de côté"
task365 budget balance Courant --date 2026-12-31
```

### `sport` : activités sportives

```bash
task365 sport add <activité> [--duration MIN] [--distance KM] [--calories KCAL]
                             [--hr BPM] [--effort 1-10] [--date DATE]
                             [--note NOTE] [--tags TAGS]
task365 sport list [--activity TYPE] [--since DATE] [--until DATE] [--tag TAG] [--limit N]
task365 sport summary [--since DATE] [--until DATE]
task365 sport edit <id> [mêmes options que add]
task365 sport rm <id>
```

```bash
task365 sport add course -D 45 -k 8.2 --hr 145 --effort 7
```

### `food` : nutrition

```bash
task365 food add [libellé] [--qte TEXTE] [--kcal N] [--prot N] [--gluc N]
                 [--sat N] [--insat N] [--fibres N] [--date DATE]
                 [--meal REPAS] [--tags TAGS]
task365 food day [date]
task365 food edit <id> [--label L] [--qte Q] [--kcal N] ... [--date D] [--tags T]
task365 food rm <id>
```

Les valeurs nutritionnelles sont **déjà totalisées** (l'app ne calcule pas à
partir d'une quantité). `--qte` est purement descriptif.

```bash
task365 food add "Salade César" -q "1 bol" --kcal 560 --prot 22 --gluc 30 -M midi
task365 food day
```

### Interfaces

```bash
task365 web     # fenêtre de bureau (recommandée)
task365 tui     # interface interactive terminal
task365 gui     # fenêtre de bureau alternative (DearPyGui)
```

### Commandes transverses

```bash
task365 dashboard [--days N]     # tableau de bord (horizon en jours, défaut 7)
task365 search <terme>           # recherche : texte, #tag, date ou métrique
task365 tags                     # liste tous les tags utilisés
task365 metric <nom> [--limit N] # historique d'une métrique (poids, humeur…)
task365 export                   # exporte toute la base en JSON
```

```bash
task365 search "#travail"
task365 metric poids --limit 30
task365 export > sauvegarde.json
```

---

## Où sont stockées les données ?

Toutes les données vivent dans une base SQLite unique, en local :

```
~/.task365/task365.db                          (Linux et macOS)
C:\Users\<VotreNom>\.task365\task365.db        (Windows)
```

Rien n'est envoyé sur Internet. Pour **sauvegarder** ou **transférer** vos
données vers une autre machine, il suffit de copier ce fichier. Pour **repartir
de zéro**, supprimez-le (il sera recréé au prochain lancement).

`task365 export` produit également un export JSON complet, utile comme sauvegarde
lisible ou pour migrer vers un autre outil.

> **Migration depuis une version antérieure** : si une base issue d'une ancienne
> version existe (`~/.shellbots/shellbots.db`), Task365 la reprend
> automatiquement au premier lancement, sans perte de données.

### Transférer sa base vers une autre machine

```bash
# sur la nouvelle machine, AVANT le premier lancement (Linux / macOS)
mkdir -p ~/.task365
cp /chemin/vers/la/copie.db ~/.task365/task365.db
```

Sous Windows (PowerShell) :

```powershell
mkdir "$env:USERPROFILE\.task365" -Force
copy C:\chemin\vers\la\copie.db "$env:USERPROFILE\.task365\task365.db"
```

Le dossier `.task365` est masqué par défaut. Sur macOS, `Cmd + Shift + .`
affiche les dossiers cachés dans le Finder et `Cmd + Shift + G` permet d'y aller
directement. Sous Windows, saisissez `%USERPROFILE%\.task365` dans la barre
d'adresse de l'Explorateur.

---

## Arborescence du dépôt

```
Task365/
├── task365/                 # le package Python
│   ├── __init__.py
│   ├── __main__.py          # permet « python -m task365 »
│   ├── cli.py               # ligne de commande + routage des interfaces
│   ├── db.py                # TOUTE la logique métier + accès SQLite
│   ├── display.py           # rendu terminal (Rich)
│   ├── tui.py               # interface interactive terminal (Textual)
│   ├── desktop.py           # interface bureau alternative (DearPyGui)
│   ├── webview_app.py       # interface bureau principale + HTML/CSS/JS embarqués
│   └── utils.py             # utilitaires (dates, tags…)
├── pyproject.toml           # métadonnées, dépendances, extras
├── README.md
├── LICENSE                  # MIT
└── .gitignore
```

**Principe de conception** : toute la logique métier est centralisée dans
`db.py`. Les interfaces (CLI, TUI, DearPyGui, fenêtre web) ne font qu'appeler ces
mêmes fonctions, sans aucune duplication. C'est ce qui permet d'ajouter une interface
(par exemple un serveur web pour y accéder depuis une tablette) sans réécrire le
cœur.

Le schéma de la base est volontairement **générique** : la table `entries`
accueille tâches, entrées de journal, contacts, notes, opérations budget, sport
et alimentation, distinguées par un champ `type`, avec des tags et des métriques
chiffrées libres. Ajouter un nouveau type d'information ne demande donc pas de
changer le schéma.

---

## Contribuer

Les contributions sont bienvenues. Le point d'entrée pour comprendre le projet
est `db.py` (le modèle de données et toutes les opérations) ; chaque interface
est une couche mince au-dessus.

---

## Licence

Distribué sous licence **MIT**. Voir le fichier [LICENSE](LICENSE).
