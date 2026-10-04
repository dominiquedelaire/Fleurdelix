# Unibox pour Fleurdelix OS et web (pc, mac, téléphones, tablettes, ...)

Vingt quais à dégager. Chaque caisse doit finir sur sa marque au sol, et on
pousse, on ne tire jamais.

Vous êtes cariste sur un quai de nuit. Le travail paraît simple : il y a autant
de caisses que d'emplacements, et il suffit de les amener à bon port. Sauf
qu'une caisse ne se tire pas. Poussée dans un angle, elle y reste pour de bon,
et le quai est perdu. L'ordre dans lequel on s'y prend décide de tout.

Le plateau est en vue isométrique : un entrepôt vu de trois quarts, caisses de
chêne, murs bas, et un faisceau de lumière au-dessus de chaque emplacement
encore libre.

<img width="2560" height="1440" alt="Screenshot_20261003_163318" src="https://github.com/user-attachments/assets/cfd648fd-731a-48ac-ab29-98bd1cdf1146" />


---

## Où jouer

**Sur Fleurdelix OS** : Unibox est intégré au système. Rien à installer.

**Dans un navigateur** : démo en ligne sur [fleurdelix.quebec](https://fleurdelix.quebec),
sur ordinateur, téléphone et tablette.

La version web s'ajoute à l'écran d'accueil d'un téléphone ou d'une tablette
depuis le menu de partage du navigateur ("Ajouter à l'écran d'accueil"). Elle
se lance alors en plein écran, sans barre d'adresse, et **reste jouable sans
connexion** une fois la première visite faite , dans le métro, en avion, ou
simplement hors réseau.

---

## Le principe

| Symbole à l'écran | Ce que c'est |
|---|---|
| Caisse de chêne | à déplacer |
| Losange turquoise au sol | un emplacement à remplir |
| Caisse turquoise | une caisse bien posée |
| Faisceau de lumière | un emplacement encore vide |

Un niveau est gagné quand toutes les caisses sont sur leurs marques. Il n'y a
ni chronomètre ni compte de coups limité : prenez le temps qu'il faut.

Deux pièges à connaître. Une caisse poussée contre un angle de mur ne peut plus
bouger dans aucune direction. Et deux caisses côte à côte le long d'un mur se
bloquent mutuellement. Dans les deux cas, rien n'est perdu : il suffit
d'annuler.

---

## Les commandes

| Action | Clavier et souris | Au doigt |
|---|---|---|
| Marcher, pousser | flèches, ou ZQSD / WASD | balayage, ou pavé directionnel |
| Rejoindre une case | clic sur la case | appui sur la case |
| Pousser une caisse | clic sur une caisse voisine | appui sur une caisse voisine |
| Annuler le dernier coup | `U` | bouton **Annuler** |
| Recommencer le quai | `R` | bouton **Recommencer** |
| Choisir un quai | `L` | bouton **Choisir un niveau** |
| Quai suivant, précédent | `N`, `P` | flèches au-dessus du plateau |

Quelques précisions qui changent le confort de jeu :

- **Le cariste trouve son chemin seul.** Cliquez ou appuyez sur une case
  lointaine : il y va par le plus court trajet, en contournant les caisses.
  Pas besoin de le piloter case par case pour faire le tour d'un mur.
- **Le balayage s'enchaîne.** Un glissement continu du doigt sur le plateau
  fait avancer pas à pas sans relâcher.
- **Les deux façons de viser fonctionnent.** En vue isométrique les directions
  sont en diagonale à l'écran. Un balayage horizontal ou vertical suit la
  flèche correspondante du pavé ; un balayage en diagonale désigne l'endroit
  où le cariste se rend.
- **Le pavé directionnel se maintient.** Garder le doigt appuyé enchaîne les
  pas dans la même direction.
- **L'annulation n'a pas de limite.** Elle remonte tout l'historique du quai,
  coup par coup, depuis le début. Une erreur ne force jamais à recommencer.

---

## Ce que le jeu retient

Sur le bandeau d'information, pendant la partie :

- le nombre de **pas** et de **poussées** en cours ;
- les **caisses posées** sur le total ;
- votre **meilleur score** sur ce quai.

À la fin d'un quai, le jeu affiche votre résultat et le minimum connu de
poussées. Terminer un quai en ce nombre exact de poussées affiche la mention
*Poussées optimales*, c'est la vraie difficulté, bien au-delà du simple fait
de finir.

La progression est gardée sur l'appareil : meilleur score de chaque quai, quais
débloqués, son activé ou non. Les quais s'ouvrent au fur et à mesure, et
l'écran de sélection montre d'un coup d'œil ceux qui sont faits, celui en cours
et ceux qui restent.

Le **son** : pas, poussées, caisse qui se pose, fanfare de fin, se coupe d'un
clic sur "Son activé", en bas du bandeau.

---

## Les vingt quais

La difficulté monte d'une caisse et deux poussées jusqu'à quatre caisses et
vingt-trois poussées. Chaque quai a son plan et son piège.

| | Quai | Caisses | Minimum |
|---|---|---|---|
| 1 | Prise en main | 1 | 2 poussées |
| 2 | Petit quai | 1 | 5 |
| 3 | La réserve | 2 | 7 |
| 4 | Le pilier | 2 | 8 |
| 5 | Autour du bloc | 2 | 9 |
| 6 | Le croisement | 2 | 11 |
| 7 | Les angles coupés | 2 | 12 |
| 8 | Deux allées | 3 | 10 |
| 9 | Retour de tournée | 3 | 12 |
| 10 | Le carré | 3 | 13 |
| 11 | Le té | 3 | 14 |
| 12 | Le muret | 3 | 15 |
| 13 | Les îlots | 3 | 16 |
| 14 | Petit dédale | 3 | 17 |
| 15 | Dédale de nuit | 3 | 18 |
| 16 | Grand hall | 3 | 20 |
| 17 | Les plots | 3 | 21 |
| 18 | Quai large | 4 | 19 |
| 19 | Contre-allée | 4 | 20 |
| 20 | Dernier quai | 4 | 23 |

Les deux premiers quais tiennent lieu d'apprentissage. À partir du huitième, le
nombre de caisses compte moins que leur ordre : savoir laquelle poser en
dernier devient le cœur du problème.

---

## Confort et accessibilité

Le jeu s'adapte à l'écran : plateau redimensionné pour tenir en entier, bandeau
replié sous le plateau sur mobile, pavé directionnel affiché dès qu'un écran
tactile est détecté, y compris sur une tablette en paysage, large mais sans
clavier.

Les animations sont raccourcies si le système est réglé sur "réduire les
animations". L'interface reste zoomable ; seul le plateau ignore le
double-appui, pour ne pas zoomer au milieu d'un geste.

---

## Logiciel libre

Unibox est open source, et le code est fourni. Vous pouvez le lire, le
modifier, le redistribuer, dessiner vos propres quais ou repartir du moteur
pour autre chose.



---

*Fleurdelix OS · Souverain · Libre · Pour demain*
