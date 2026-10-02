# ERPNext sur Fleurdelix OS
<img width="1672" height="941" alt="erpnextcrmfleurdelix" src="https://github.com/user-attachments/assets/b340e019-1bbc-4556-8fc1-176f718dfa9b" />

**L'ERP et CRM libre retenu pour Fleurdelix OS, présenté module par module.**

Fleurdelix OS est un système d'exploitation souverain. Pour la gestion d'entreprise, nous avons retenu **ERPNext**, un ERP et CRM complet, publié sous licence libre GPL v3. Il n'existe pas d'édition « Entreprise » payante : tous les modules décrits ici font partie de la version libre, sans frais de licence.

Cette page décrit ce que chaque module permet de faire, et où le trouver dans l'interface. Elle porte sur **ERPNext version 16**.



---

## Table des matières

- [Pourquoi ERPNext](#pourquoi-erpnext)
- [Vue d'ensemble](#vue-densemble)
- [Les modules](#les-modules)
  - [CRM](#crm)
  - [Ventes et point de vente](#ventes-et-point-de-vente)
  - [Achats](#achats)
  - [Stock et inventaire](#stock-et-inventaire)
  - [Fabrication](#fabrication)
  - [Sous-traitance](#sous-traitance)
  - [Projets](#projets)
  - [Comptabilité](#comptabilité)
  - [Actifs](#actifs)
  - [Qualité](#qualité)
  - [Support](#support)
  - [Organisation et paramètres](#organisation-et-paramètres)
  - [Site web et portail clients](#site-web-et-portail-clients)
- [Pour aller plus loin : les apps complémentaires](#pour-aller-plus-loin--les-apps-complémentaires)
- [Adaptation au Québec](#adaptation-au-québec)
- [Installation](#installation)
- [Licence et marques](#licence-et-marques)

---

## Pourquoi ERPNext

- **Entièrement libre.** Code source ouvert sous GPL v3, sans édition payante incluant des fonctions essentielles comme la comptabilité complète.
- **Vos données chez vous.** Déploiement sur votre propre serveur ou en local. Aucune dépendance à un nuage étranger.
- **Complet.** Un seul système pour la relation client, les ventes, les achats, les stocks, la production, la comptabilité et les projets.
- **Extensible.** ERPNext repose sur le framework libre Frappe : on l'adapte avec des apps qui s'ajoutent par-dessus, sans toucher au cœur.
- **En français.** L'interface est traduite, et un plan comptable pour les provinces francophones du Canada est fourni.

---

## Vue d'ensemble

| Module | Ce qu'il couvre |
|---|---|
| [CRM](#crm) | Pistes, opportunités, prospects, campagnes, rendez-vous |
| [Ventes et point de vente](#ventes-et-point-de-vente) | Devis, commandes clients, factures, caisse, fidélisation |
| [Achats](#achats) | Demandes d'achat, appels d'offres, commandes fournisseurs |
| [Stock et inventaire](#stock-et-inventaire) | Entrepôts, mouvements, lots, numéros de série, valorisation |
| [Fabrication](#fabrication) | Nomenclatures, ordres de fabrication, planification (MRP) |
| [Sous-traitance](#sous-traitance) | Production confiée à un tiers, et production pour un tiers |
| [Projets](#projets) | Tâches, feuilles de temps, coûts et facturation de projets |
| [Comptabilité](#comptabilité) | Facturation, paiements, banque, budgets, taxes, états financiers |
| [Actifs](#actifs) | Immobilisations, amortissements, entretien |
| [Qualité](#qualité) | Objectifs, inspections, non-conformités, actions correctives |
| [Support](#support) | Billets clients, ententes de service, garanties |
| [Organisation et paramètres](#organisation-et-paramètres) | Sociétés, départements, utilisateurs, permissions |
| [Site web et portail clients](#site-web-et-portail-clients) | Site public, portail clients et fournisseurs |

---

## Les modules

### CRM

Le CRM suit tout le parcours commercial, du premier contact jusqu'au client. Une **piste** devient une **opportunité**, puis un devis dans le module Ventes.

**Fonctionnalités principales**

- **Pistes** (contacts non qualifiés) et **opportunités**, avec étape de vente et probabilité
- **Prospects** : les entreprises ciblées et leurs contacts
- **Clients, contacts** et **contrats**
- **Rendez-vous** et historique des communications
- **Campagnes**, campagnes de courriel, groupes de diffusion et envoi de SMS
- **Maintenance** : calendriers et visites d'entretien, réclamations sous garantie
- **Paramétrage** : territoires, groupes de clients, représentants, étapes de vente, sources de pistes
- **Rapports** : entonnoir de ventes, pipeline, analyse des ventes, efficacité des campagnes, temps de première réponse

**Où le trouver :** menu **CRM**, ou `/app/crm`.

> ℹ️ Dans ERPNext 16, l'icône CRM est masquée par défaut, même si le module est installé et fonctionnel. On la réaffiche dans *Desktop Icon* › *CRM*, en décochant *Hidden*.

<img width="1920" height="1080" alt="Screenshot_20261002_161438" src="https://github.com/user-attachments/assets/8c2eaea8-96d3-4129-944b-d826fed4d39f" />


---

### Ventes et point de vente

Le module Ventes gère le cycle complet, du devis à la facture, et inclut un **point de vente** pour la vente au comptoir.

**Fonctionnalités principales**

- **Devis**, **commandes clients** et **factures de vente**
- **Articles et prix** : articles, groupes d'articles, listes de prix, prix par article, règles de prix et promotions
- **Point de vente** : écran de caisse utilisable sur tablette, profils de caisse, factures POS, ouverture et clôture de caisse
- **Programme de fidélité** et points de fidélité
- **Rapports** : analyse des ventes, tendances, marge brute

**Où le trouver :** menu **Ventes** (*Selling*), ou `/app/selling`. La caisse s'ouvre à `/app/point-of-sale`.

<img width="1920" height="1080" alt="Screenshot_20261002_161627" src="https://github.com/user-attachments/assets/3699bd7a-77b8-4475-bf8d-fe4e62785aa6" />

<img width="1920" height="1080" alt="Screenshot_20261002_161701" src="https://github.com/user-attachments/assets/8ed1fc75-bcd9-42e1-b2aa-091ee332ab41" />





---

### Achats

Le module Achats couvre l'approvisionnement, du besoin exprimé jusqu'à la facture fournisseur.

**Fonctionnalités principales**

- **Demandes de matériel**, **appels d'offres** et **devis fournisseurs**, avec tableau comparatif
- **Commandes fournisseurs** et **factures d'achat**
- **Fournisseurs** et groupes de fournisseurs
- **Évaluation des fournisseurs** : fiches d'évaluation, critères et classements
- **Rapports** : analyse des achats, suivi des commandes, articles à commander, historique par article

**Où le trouver :** menu **Achats** (*Buying*), ou `/app/buying`.

<img width="1920" height="1080" alt="Screenshot_20261002_161903" src="https://github.com/user-attachments/assets/9502c9dc-4f9b-4534-bc6a-c7b31be5924c" />


---

### Stock et inventaire

Le module Stock suit chaque article, dans chaque entrepôt, à chaque mouvement.

**Fonctionnalités principales**

- **Mouvements de stock**, **réceptions d'achat** et **bons de livraison**
- **Listes de prélèvement**, bordereaux d'emballage et tournées de livraison
- **Lots** et **numéros de série**, avec traçabilité complète et suivi des dates d'expiration
- **Variantes d'articles** (taille, couleur…), marques et unités de mesure avec conversion
- **Inventaire physique** et rapprochement de stock
- **Frais d'approche** : transport et douane intégrés au coût des articles
- **Inspections de qualité** à la réception ou à la livraison
- **Rapports** : grand livre et solde de stock, quantités projetées, vieillissement du stock, niveaux de réapprovisionnement

**Où le trouver :** menu **Stock**, ou `/app/stock`.

<img width="1920" height="1080" alt="Screenshot_20261002_162039" src="https://github.com/user-attachments/assets/d3f9f209-95ed-4ab8-bb46-6c0ed33425d1" />

---

### Fabrication

Le module Fabrication planifie et suit la production, des matières premières au produit fini.

**Fonctionnalités principales**

- **Nomenclatures** (*BOM*), avec un outil de création, de comparaison et de mise à jour en lot
- **Ordres de fabrication** et **fiches de travail** par opération
- **Planification des besoins** : plans de production, programme directeur de production, prévisions de ventes, délais d'approvisionnement
- **Postes de travail**, opérations, gammes et plan d'atelier
- **Temps d'arrêt** et leur analyse
- **Rapports** : analyse de production, synthèse des ordres et des fiches de travail, matières consommées

**Où le trouver :** menu **Production** (*Manufacturing*), ou `/app/manufacturing`.

<img width="1920" height="1080" alt="Screenshot_20261002_162229" src="https://github.com/user-attachments/assets/36ba0185-95d4-48e8-b2fe-18570901856d" />


---

### Sous-traitance

Ce module gère la production confiée à un sous-traitant, et la production que vous réalisez pour un client avec ses propres matières.

**Fonctionnalités principales**

- **Sous-traitance sortante** : commandes de sous-traitance, envoi des matières, réception des produits finis
- **Sous-traitance entrante** : commandes reçues d'un client, livraison des produits transformés
- **Nomenclatures de sous-traitance**
- **Rapports** : synthèse des commandes, matières à transférer, articles à recevoir

**Où le trouver :** menu **Sous-traitance** (*Subcontracting*), ou `/app/subcontracting`.

<img width="1920" height="1080" alt="Screenshot_20261002_162401" src="https://github.com/user-attachments/assets/1fbd2e56-cd1d-4e0d-8ee7-3de10503ce6b" />


---

### Projets

Le module Projets organise le travail et en mesure le coût, ce qui permet de facturer le temps passé.

**Fonctionnalités principales**

- **Projets** et **tâches**, avec dépendances et modèles de projet
- **Feuilles de temps**, types d'activités et coûts par activité
- **Facturation du temps** à partir des feuilles de temps
- **Mises à jour de projet** pour le suivi d'avancement
- **Rapports** : synthèse de projet, tâches en retard, résumé quotidien des feuilles de temps, stock consommé par projet

**Où le trouver :** menu **Projets** (*Projects*), ou `/app/projects`.

<img width="1920" height="1080" alt="Screenshot_20261002_162522" src="https://github.com/user-attachments/assets/6df0f36d-8c75-4ea0-9e34-37abd1064dd4" />


---

### Comptabilité

La comptabilité est complète dans la version libre, à partie double. Dans ERPNext 16, elle est regroupée dans un dossier **Comptabilité** (*Accounting*), qui contient les sous-menus ci-dessous.

#### Facturation

- Plan comptable
- **Comptes clients** : factures de vente, notes de crédit, comptes à recevoir
- **Comptes fournisseurs** : factures d'achat, notes de débit, comptes à payer
- Grand livre et balance de vérification

<img width="1920" height="1080" alt="Screenshot_20261002_162629" src="https://github.com/user-attachments/assets/fd98c43f-8d2e-485f-baaa-37273ea1eed8" />

<img width="1920" height="1080" alt="Screenshot_20261002_162828" src="https://github.com/user-attachments/assets/284b7d6f-51cd-4a10-a69c-28f2cb5ce892" />




#### Paiements

- Écritures de paiement et écritures de journal
- Demandes et ordres de paiement
- **Lettrage des paiements**, manuel ou automatique

#### Banque

- Comptes bancaires
- **Rapprochement bancaire** et état de rapprochement
- Garanties bancaires
- **Relances** des factures impayées

#### Budget

- **Budgets** par centre de coûts ou par projet, avec contrôle des dépassements
- Centres de coûts et répartition entre centres
- Dimensions comptables personnalisées (succursale, région…)
- Rapport d'écart budgétaire

#### Taxes

- Modèles de taxes de vente et d'achat, taxes par article
- Catégories et règles de taxes
- Retenues à la source

#### Rapports financiers

- **Bilan**, **état des résultats** et **flux de trésorerie**
- Balance de vérification, rapports consolidés multisociétés
- États financiers personnalisés à partir de modèles
- Grands livres clients et fournisseurs, journaux des ventes et des achats
- **Rentabilité** : marge brute, analyse de rentabilité



#### Abonnements

- Plans et abonnements, avec **facturation récurrente** automatique

#### Gestion des actions

- Registre des actionnaires, transferts et soldes d'actions

**Où le trouver :** dossier **Comptabilité** dans le menu principal. La facturation est à `/app/invoicing` et les rapports financiers à `/app/financial-reports`.

---

### Actifs

Le module Actifs gère les immobilisations tout au long de leur vie.

**Fonctionnalités principales**

- **Registre des immobilisations** par catégorie et par emplacement
- **Amortissements** calculés automatiquement selon un calendrier, et ajustements de valeur
- **Capitalisation** d'actifs et déplacements entre emplacements
- **Entretien** : équipes, calendriers et journal d'entretien
- **Réparations**
- **Rapports** : registre des immobilisations, grand livre des amortissements, activité des actifs

**Où le trouver :** menu **Actifs** (*Assets*), ou `/app/assets`.

<img width="1920" height="1080" alt="Screenshot_20261002_162951" src="https://github.com/user-attachments/assets/9b98d41a-c10e-4b55-80fa-cca7d9c1e962" />


---

### Qualité

Le module Qualité structure une démarche d'amélioration continue.

**Fonctionnalités principales**

- **Objectifs qualité** et revues périodiques
- **Procédures qualité** documentées
- **Inspections**, avec modèles réutilisables
- **Non-conformités** et **actions correctives**
- **Rétroaction** des clients ou des employés, avec modèles de questionnaire
- **Réunions qualité**

**Où le trouver :** menu **Qualité** (*Quality*), ou `/app/quality`.

<img width="1920" height="1080" alt="Screenshot_20261002_163053" src="https://github.com/user-attachments/assets/0d093dcc-a453-4194-803d-58d94103adf1" />


---

### Support

Le module Support gère les demandes des clients après la vente.

**Fonctionnalités principales**

- **Billets** (*Issues*), avec type et priorité
- **Ententes de niveau de service**, avec délais de réponse et de résolution
- **Calendriers et visites d'entretien**
- **Réclamations sous garantie**
- **Rapport** sur le temps de première réponse

**Où le trouver :** menu **Support**, ou `/app/support`.

> ℹ️ Comme le CRM, l'icône Support est masquée par défaut dans ERPNext 16. On la réaffiche de la même façon.



---

### Organisation et paramètres

C'est ici qu'on configure la structure de l'entreprise et les accès.

**Fonctionnalités principales**

- **Sociétés** (multisociété), succursales et départements
- **En-têtes de lettre** pour les documents imprimés
- **Utilisateurs**, rôles et **permissions** détaillées par rôle
- **Comptes de courriel** pour l'envoi et la réception
- Paramètres généraux d'ERPNext

**Où le trouver :** menus **Organisation** et **Paramètres ERPNext**.

<img width="1920" height="1080" alt="Screenshot_20261002_163220" src="https://github.com/user-attachments/assets/16604c06-3068-4933-8cad-ed4f099377c1" />


<img width="1920" height="1080" alt="Screenshot_20261002_163333" src="https://github.com/user-attachments/assets/5a17a43f-9715-430e-8c55-cd63ca6a1c3d" />

---

### Site web et portail clients

Fourni par le framework Frappe, sur lequel repose ERPNext.

**Fonctionnalités principales**

- **Site web public** : pages, blogue, formulaires web
- **Portail clients** : consultation des devis, commandes, factures et billets de support
- **Portail fournisseurs** : réponse aux appels d'offres

**Où le trouver :** menu **Site web** (*Website*).


---

## Pour aller plus loin : les apps complémentaires

D'autres apps libres, du même éditeur, s'installent par-dessus ERPNext :

| App | Ce qu'elle ajoute |
|---|---|
| **Frappe HR** | Ressources humaines et paie : employés, congés, présences, recrutement, notes de frais, paie |
| **Frappe CRM** | Une interface CRM plus moderne, qui se connecte à ERPNext |
| **Helpdesk** | Un service d'assistance complet, avec portail client |



---

## Installation

Sur Fleurdelix OS, ERPNext se déploie avec Docker, à partir du dépôt officiel [`frappe_docker`](https://github.com/frappe/frappe_docker) :

- **Code :** `/opt/fleurdelix/erpnext`
- **Configuration :** `/etc/fleurdelix/erpnext`
- **Données :** `/var/lib/fleurdelix/erpnext` (base MariaDB et fichiers du site)
- **Accès :** `http://<adresse-de-la-machine>:8090`

L'installation fonctionne aussi bien sur un serveur que sur un poste local.

---

## Licence et marques

- **ERPNext** est un logiciel libre sous licence **GPL v3**, développé par Frappe Technologies et ses contributeurs.
- Le **framework Frappe** est publié sous licence **MIT**.
- **ERPNext** et son logo sont des marques de commerce de Frappe Technologies Pvt. Ltd. Fleurdelix OS n'est ni affilié à Frappe Technologies ni approuvé par elle ; ERPNext est cité ici pour décrire le logiciel retenu.

**Liens utiles :**

- [Site officiel d'ERPNext](https://frappe.io/erpnext)
- [Code source d'ERPNext](https://github.com/frappe/erpnext)
- [Documentation d'ERPNext](https://docs.frappe.io/erpnext)
- [Forum de la communauté](https://discuss.frappe.io)

---

*Fleurdelix OS · Souverain · Libre · Pour demain*
