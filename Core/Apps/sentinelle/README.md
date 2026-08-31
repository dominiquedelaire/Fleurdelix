# Sentinelle pour Fleurdelix OS

**Un exemple de contrôleur local pour agents IA.** La sentinelle se place entre
un agent et ses outils, enregistre tout ce qui passe dans un journal scellé,
caviarde les secrets avant de les écrire, et peut retenir ou refuser un appel.

Tout reste sur la machine : un fichier SQLite, aucun service, aucun compte,
aucun conteneur.

> **Ceci est un projet d'exemple dans Fleurdelix OS.** Il est écrit pour montrer
> comment on construit ce genre de dispositif et pour rendre les décisions de
> conception discutables. 

---
<img width="1807" height="914" alt="Ecran de visualisation Sentinelle" src="https://github.com/user-attachments/assets/9b5d301e-598a-47f2-ac49-21f3125c695b" />


## Voir en trois commandes

```bash
pip install -e .
sentinelle demo      # trois sessions fictives, dont deux qui dérapent
sentinelle ui        # ou : sentinelle ui --navigateur
```

## Le problème

Un agent local ou cloud qui a accès à votre système de fichiers, à votre dépôt Git et au réseau
peut faire, en trente secondes et sans mauvaise intention, quelque chose que tu
n'aurais jamais approuvé. Le journal du terminal ne suffit pas à le
reconstituer après coup, et une confirmation à chaque appel serait ignorée dès
le dixième clic.

Ce projet explore une position précise : **le point de passage**. L'agent parle
à ses outils par un protocole, MCP, en JSON-RPC ligne par ligne sur stdin et
stdout. Il suffit donc de s'intercaler.

```
agent (Claude Code, Cursor…)
   ↓ stdio
sentinelle proxy        ← relaie, enregistre, décide
   ↓ stdio
serveur MCP réel (filesystem, git, github…)

        journal.db  ←  sentinelle ui
```

Côté utilisateur, l'installation consiste à glisser `sentinelle proxy --` devant
la commande du serveur, dans la configuration du client MCP. L'agent n'est pas
modifié et ne sait pas qu'il est observé.

## Les quatre briques

### 1. Un journal qu'on ne peut pas retoucher

Chaque événement contient le hash du précédent. Modifier une ligne après coup
casse la chaîne, et `sentinelle verify` dit à quel maillon.

```bash
sentinelle demo --falsifier   # modifie une ligne en douce
sentinelle verify             # → contenu falsifié à l'événement 17
```

Dans la fenêtre, le fil vertical qui relie les événements se rompt visuellement
à cet endroit. L'intégrité n'est pas un badge dans un coin : elle est dans la
structure de la liste.

### 2. Rien n'est stocké en clair

Une boîte noire qui enregistre tout devient le meilleur endroit où chercher des
secrets. Le caviardage a donc lieu **avant** le scellement : la version en clair
n'existe nulle part, et le hash porte sur ce qui est réellement stocké.

```
lu par l'agent   STRIPE_KEY=sk_live_51H8xQ2eZvKYlo2CkQm3nP
au journal       STRIPE_KEY=⟦stripe·33b7f1⟧
```

L'empreinte est un HMAC-SHA256 calculé avec une clé locale. Elle ne se retourne
pas, même pour un mot de passe court, mais **le même secret porte partout le
même marqueur**. Si un jeton lu dans `deploy.sh` réapparaît dans l'URL d'un
`fetch`, le catalogue le compte comme une seule valeur vue deux fois : la fuite
est prouvée sans que le secret ait jamais été écrit.

```bash
sentinelle secrets           # ce qui est passé, rien de lisible
sentinelle secrets 6ebd6f    # où cette valeur a circulé
```

Sont détectés : les formats connus (Stripe, AWS, GitHub, Google, Slack, OpenAI,
Anthropic, JWT, clés PEM, mots de passe dans les URL), les affectations dont le
*nom* trahit la valeur, les jetons opaques repérés à l'entropie, et les données
personnelles (courriels, cartes et NAS validés par Luhn, téléphones).

### 3. Le verdict

Chaque règle porte un mode. Par défaut, rien ne bloque.

| mode | ce qui se passe |
|---|---|
| `observe` | l'appel passe, l'alerte est consignée |
| `demande` | l'appel est retenu jusqu'à ce qu'un humain tranche |
| `bloque` | l'appel n'atteint jamais l'outil |

```yaml
regles:
  - id: fuite-possible
    description: un secret a été lu dans cette session, puis quelque chose est sorti
    severite: critique
    mode: bloque
    sequence:
      - marque: secret
      - outil: ["fetch", "http_post", "git_push", "send_email"]
```

Cette règle de séquence est le cœur du moteur : aucune des deux actions n'est
répréhensible isolément, c'est leur enchaînement qui l'est. Le marquage de
provenance (« ici l'agent a lu un secret ») rend la chose détectable sans
analyse de flux complète.

Quand une règle est en `demande`, l'agent attend et la demande apparaît des deux
côtés :

```bash
sentinelle demandes
sentinelle accorder 1 --motif "c'est moi qui l'ai demandé"
```

Et un frein d'urgence, indépendant des règles :

```bash
sentinelle stop --motif "je reprends la main"
sentinelle go
```

### 4. Des compteurs

Plafonds en nombre d'appels, en coût estimé, en octets rapportés. Portées
`session · heure · jour · semaine · glissante · toujours`, avec les mêmes modes
que les règles.

```bash
sentinelle budget
#   appels-par-session
#     █░░░░░░░░░░░░░░░░░░░░░░░ 9 / 300 appels  demande
```

## Les décisions qui méritent d'être discutées

C'est la partie intéressante d'un projet d'exemple. Chacune de ces décisions
pouvait être prise autrement.

**Le refus est écrit pour être lu par le modèle, pas par toi.** Un agent qui
reçoit une erreur de protocole réessaie souvent en boucle. Un agent qui reçoit
un résultat d'outil disant ce qui a été refusé, quelle règle, et quoi faire
ensuite, change de plan. Le refus part donc en `isError` dans un résultat
normal, avec une consigne explicite de ne pas chercher un autre chemin vers le
même effet.

**En cas de doute, on refuse.** Moteur de règles en erreur, humain qui ne répond
pas dans le délai, journal inaccessible : l'appel ne passe pas. Un dispositif de
contrôle dont l'inaction laisse passer ne contrôle rien. C'est réglable
(`si_erreur: laisser`) parce que l'argument inverse se défend aussi : un bug
dans une expression régulière qui paralyse ton agent est un bon moyen de te
faire désinstaller l'outil.

**Aucun modèle de langage ne rend de verdict.** Un juge non déterministe, c'est
un juge qu'on peut convaincre. Toutes les règles sont du code, et une alerte
doit être reproductible et explicable. Un LLM aurait sa place pour trier ce qui
mérite un œil humain, jamais pour décider.

**Les compteurs ne sont stockés nulle part.** Ils sont recalculés depuis le
journal scellé à chaque affichage. Un compteur qu'on peut remettre à zéro sans
laisser de trace ne vaut rien, et un chiffre dérivé n'a pas à être scellé : le
fait qui le produit l'est déjà.

**Un appel refusé ne consomme pas de budget.** Sinon la sentinelle punit deux
fois : elle bloque l'appel, puis fait payer au suivant un budget dépensé par un
appel qui n'a jamais eu lieu.

**On peut effacer sans casser la preuve.** Le sceau porte le *hash* du contenu,
pas le contenu. Détruire un contenu après coup laisse donc la chaîne intacte :
on prouve toujours que quelque chose est passé là, sans plus pouvoir le lire.
C'est la réponse au conflit entre journal immuable et droit à l'effacement.

```bash
sentinelle oublier --secret <empreinte> --motif "demande du client"
sentinelle verify
# chaîne intacte, 52 événements vérifiés
# contenus : 17 intacts, 1 effacés (chaîne préservée)
```

**La demande d'autorisation passe par une file en base**, pas par le terminal.
Stdin et stdout appartiennent déjà au dialogue avec l'agent : il n'existe aucun
moyen de poser une question dans le terminal sans corrompre le canal.

## Trois bugs instructifs

Ils valent d'être racontés parce qu'aucun n'apparaît en lisant le code.

**L'identifiant JSON-RPC.** Le refus renvoyait `"id": "1"` en chaîne là où le
client avait envoyé l'entier `1`. Un client strict n'aurait jamais fait le
rapprochement et serait resté à attendre une réponse déjà arrivée : un agent
figé indéfiniment, par la fonctionnalité censée le protéger.

**Les chemins ont l'entropie d'un secret.** `/home/toi/projets/facturier/taxes`
passe largement le seuil d'un jeton opaque. La première version caviardait tous
les chemins et rendait la chronologie illisible. Trois garde-fous : pas de barre
oblique, pas d'hexadécimal pur (un sha git n'est pas un secret), au moins deux
classes de caractères.

**Le décalage d'un appel.** Avec un plafond de 3, seuls 2 appels passaient :
l'événement de l'appel en cours est déjà inscrit au journal quand les budgets
sont évalués, et je le comptais une seconde fois. Un dispositif qui coupe une
action de trop est aussi cassé qu'un dispositif qui en laisse passer une.

Les deux jeux de tests gardent ces trois cas :

```bash
python3 tests_redaction.py   # 23 cas, dans les deux sens
python3 tests_controle.py    # 9 scénarios contre un vrai proxy
```

Les cas de caviardage comptent autant dans un sens que dans l'autre : trop peu
et le journal devient un coffre à secrets, trop et il devient illisible.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .            # pyyaml seulement
pip install pywebview       # pour la fenêtre
```

Sous Fleurdelix OS (préinstallé), ou Linux Ubuntu, pywebview a besoin d'un moteur de rendu :

```bash
sudo apt install python3-gi gir1.2-webkit2-4.1 libcairo2-dev
```

Sur macOS et Windows, rien à installer. En cas de souci,
`sentinelle ui --navigateur` sert exactement la même interface dans le
navigateur.

## Brancher un vrai agent

Dans la configuration MCP de ton client, glisse `sentinelle proxy --` devant la
commande du serveur. Les chemins doivent être **absolus** : le client lance le
proxy depuis un répertoire courant que tu ne contrôles pas.

```json
{
  "mcpServers": {
    "fichiers": {
      "command": "/chemin/vers/.venv/bin/sentinelle",
      "args": ["proxy", "--observer",
               "--regles", "/chemin/vers/regles.yaml",
               "--",
               "npx", "-y", "@modelcontextprotocol/server-filesystem",
               "/chemin/vers/projets"]
    }
  }
}
```

Garde `--observer` les premiers jours : rien n'est bloqué, tout est enregistré,
et `sentinelle check` te dira ce que chaque règle aurait attrapé. Tu enlèves le
drapeau quand les chiffres te paraissent justes.

Le proxy ne peut rien écrire sur la sortie standard sans casser le protocole :
ses diagnostics vont dans `~/.sentinelle/proxy.log`. C'est le premier endroit à
regarder.

Pour essayer sans client MCP, un faux serveur est fourni :

```bash
sentinelle proxy -- python3 faux_serveur_mcp.py < exemple_session.jsonl
```

## Les commandes

| Commande | Ce qu'elle fait |
|---|---|
| `sentinelle proxy -- <cmd>` | relaie un serveur MCP et enregistre |
| `sentinelle runs` / `show <id>` | les sessions, puis le détail de l'une |
| `sentinelle verify` | recalcule la chaîne de hash |
| `sentinelle check` | rejoue les règles sur tout l'historique |
| `sentinelle budget` | où en sont les compteurs |
| `sentinelle demandes` | les autorisations en attente |
| `sentinelle accorder` / `refuser <id>` | trancher |
| `sentinelle stop` / `go` | frein d'urgence |
| `sentinelle secrets [empreinte]` | ce qui est passé sans être gardé |
| `sentinelle rediger [fichier]` | essaie le caviardage sur un texte |
| `sentinelle oublier` | détruit un contenu, garde le sceau |
| `sentinelle ui` | ouvre la fenêtre |
| `sentinelle export f.json` | sort le journal complet |

## Architecture

```
sentinelle/
  db.py           schéma SQLite (WAL : le proxy écrit pendant que l'UI lit)
  journal.py      écriture chaînée par hash + vérification
  proxy.py        relais MCP stdio, deux threads, zéro logique métier
  redaction.py    caviardage avant scellement + empreintes HMAC
  controle.py     le verdict : blocage, file d'autorisations, frein
  budgets.py      compteurs, fenêtres, plafonds
  regles.py       moteur déterministe + rejeu sur historique
  webview_app.py  pont Api, fenêtre pywebview, repli navigateur
  ui/             index.html, app.css, app.js
  cli.py          les commandes
```

Deux processus, jamais un seul : le proxy tourne quand l'agent tourne, la
fenêtre quand tu la lances. SQLite en mode WAL permet un écrivain et plusieurs
lecteurs, donc tu peux regarder l'agent travailler en direct.

`webview_app.py` ne contient aucune logique métier : la classe `Api` délègue.
Le même pont sert à la fenêtre et au mode navigateur, donc `app.js` est
identique dans les deux cas.

## Ce que ça ne fait pas

- **Le coût réel en jetons.** La sentinelle voit les appels d'outils, pas le
  dialogue avec le modèle. Le coût affiché vient d'un tarif que tu poses
  toi-même par outil. Ce n'est pas une facture.
- **Les prompts.** Même raison : il faudrait un second point d'écoute, un proxy
  HTTP vers l'API du modèle.
- **Le chiffrement au repos.** Le caviardage protège des secrets qui transitent.
  Le reste du contenu est en clair dans SQLite.
- **L'isolation.** Un agent qui peut exécuter des commandes shell peut aussi
  toucher au journal. Une vraie sentinelle vivrait dans un processus dont
  l'agent n'a pas les droits.
- **Le multi-utilisateur, l'identité, l'authentification.** C'est un outil pour
  une personne sur sa machine.

## Où se situe ce projet

Celui-ci vise une personne qui exécute des agents en local sur son ordinateur, sans serveur et sans
compte, avec une fenêtre pour regarder en temps réel.

## Licence

MIT. Voir [LICENSE](LICENSE).
