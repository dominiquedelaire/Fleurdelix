
<img width="2560" height="1440" alt="Screenshot_20260918_101346" src="https://github.com/user-attachments/assets/8befecf5-32b7-4c41-8c08-1a0441b5adc8" />


# Fonctionnalités par version   
**Auteur :** Dominique Delaire   
**Date de création initiale :** 14 juin 2025   
**Date de mise à jour :** 28 septembre 2026     

## Table des matières

- [Version Core](#version-core)
  - [Détail et fonctionnalités de la version Core version 2026.03.22](#détail-et-fonctionnalités-de-la-version-core-version-20260322)
- [Version Core IA Pro](#version-core-ia-pro)
- [Fleurdelix Mobile pour téléphones Android](#fleurdelix-mobile-pour-téléphones-android)
- [Télécharger les .Iso](#télécharger-les-iso)
    - [Les fichiers](#les-fichiers)
    - [Empreinte de la clé de signature](#empreinte-de-la-clé-de-signature)
    - [Sur Linux ou macOS](#sur-linux-ou-macos)
    - [Sur Windows](#sur-windows)
    - [Si la vérification échoue](#si-la-vérification-échoue)
    - [Ce que cette vérification prouve, et ne prouve pas](#ce-que-cette-vérification-prouve-et-ne-prouve-pas)
    - [Démarrage sécurisé (Secure Boot)](#démarrage-sécurisé-secure-boot)


# Version Core 

## Détail et fonctionnalités de la version Core version 2026.03.22
- Basé sur un noyau ubuntu server minimal 26.04.1, interface terminal
- Voici les logiciels par domaine installés sur Fleurdelix OS :
  - **Internet**
    - **Firefox** : Navigateur web
    - **Thunderbird supernova** : Gestion des courriels / emails
  - **Bureautique**
    - **OnlyOffice** : Suite bureautique compatible Microsoft et remplaçant la suite Microsoft 365. Le visualisateur et l'éditeur de PDF inclus aussi est très bien. Je l'utilise tous les jours.
    - **Nextcloud** : Gestion électronique de documents et fichiers. (équivalent de onedrive en local et bien plus)
  - **Systèmes** 
    - **Dolphin** : Gestionnaire de fichiers
    - **KDE Partition Manager** : Gestionnaire de disques et partitions
    - **Konsole** : Terminal avec fond transparent pour finetuner le système et installer des extensions et apps.
    - **Paramétrage du système** (fonds d'écran, périphériques, bluetooth, thèmes et couleurs, Réseaux, Wifi, Régions, etc...)
    - **Moniteur système** : Surveillance processeurs, disques, mémoires, ...
    - **Spectacle** : Utilitaire de capture d'écrans multi écran (images, vidéos)
    - **Info center** : Affichage des informations du système
    - **Sweeper** : Nettoie les traces sur le système (fichiers temporaires, cookies, et toutes les traces que laisse l'utilisateur pour gagner de l'espace disque)
  - **Développement**
    - **Kate** : Editeur de textes et de codes
  - **Graphiques**
    - **Blender** : Logiciel 3D et animations
    - **Gnenview** : Visualisation d'images
    - **Okular** : Visualisateur universel de documents et de différents formats de fichiers.
  - **Multimédia**
    - **Ardour** : Mixage audio multipiste
    - **Audacity** : Création ét éditions de fichiers audios
    - **Elisa** : lecteur audio et radio FM en 
    - **LMMS** : Séquenceur et création de musiques, style FL Studio
    - **Haruna** : lecteur vidéo et de streams (utilise le puissant mpv derrière)
    - **Strawberry** : lecteur de musique
  - **Applications Fleurdelix**
    - **Task365** : Gestionnaire de taĉhes et gestion de la vie personnelle et professionnelle.https://github.com/dominiquedelaire/Fleurdelix/tree/main/Core/Apps/Task365
    - **Flightboard** : Un Afficheur Temps-réel d'avions qui passent au-dessus de chez vous, façon panneau à LED d'aéroport ou scope radar de tour de contrôle. https://github.com/dominiquedelaire/Fleurdelix/tree/main/Core/Apps/flightboard
    - **Election 3d2d** : Génération en temps réel des données fournies par Election québec sur une couche 3d et 2d pour Google earth pro ou google maps my maps ou autre sig comme ArcGis, uMap, ... https://github.com/dominiquedelaire/Fleurdelix/tree/main/Core/Apps/Election3d2d
  - **Jeux Fleurdelix**
    - Nids de poule Montréal https://github.com/dominiquedelaire/Fleurdelix/tree/main/Core/Games/Nids-de-poule
  - **Divers**
    - **Google Earth Pro** : Version locale de Google Earth pour visiter la planète Terre
    

# Version Core IA Pro 
- Toutes les fonctionnalités de la version **Core** +

    - **Tal.ia** : Interface à la chatgpt pour utiliser l'IA avec différents modèles locaux ou ses propres données. Fonctionne en local sans internet.
    - **framework Shellbots** : Framework pour accélérer les projets IA de toute nature : entraînement des données, génération d'images, création de modèles prédictifs, etc...
    - **Outils pour les entreprises** pour bâtir leur propre modèle ou hériter de modèles locaux avec leurs données d'organisation
    - **Logiciels Financiers, ERP, CRM installés**
    - Autres logiciels pour entreprises :
      - Liste à venir

# Fleurdelix Mobile pour téléphones Android
- Disponible Décembre 2026
  - Plateforme mobile minimaliste remplaçant l'interface android et complétement configuratble avec de l'IA embarqué en local. Pratique pour les enfants et les personnes âgées.
 
# Télécharger les .Iso 
Utiliser un outil pour installer le fichier sur une clé ou un disque bootable ou l'utiliser directement sur un système de machine virtuelle tel que Virtual Box, Vm Ware, etc.   

**ISO Fleurdelix Core 2026.03.22** : [télécharger la version Core (4.1Gb)](https://fleurdelix.quebec/iso/fleurdelixOSCore-amd64-v20260322.iso)   
**ISO Fleurdelix Core IA Pro** : Disponible à compter du 20 octobre 2026


Toutes les images de Fleurdelix OS sont signées. Vous n'êtes pas obligés de faire cette opération mais cette vérification prend
une minute et garantit que vous avez bien reçu l'image d'origine, sans
altération en cours de route.

### Les fichiers

| Fichier | Rôle |
|---|---|
| `fleurdelixOSCore-amd64-v20260322.iso` | l'image d'installation |
| `SHA256SUMS` | l'empreinte de l'image |
| `SHA256SUMS.asc` | la signature de cette empreinte |
| `fleurdelix-signing-key.asc` | la clé publique de signature |

Téléchargez les quatre dans le même dossier.

### Empreinte de la clé de signature

```
43AB 08D4 173D A005 5D30 08F3 0EEB 9FE6 30C2 2E58
```

**Comparez-la avec celle affichée à l'étape 1 ci-dessous.** Si elles
diffèrent, la clé que vous avez téléchargée n'est pas la nôtre : arrêtez-vous
là et signalez-le.

### Sur Linux ou macOS

**1. Importer la clé publique**

```bash
gpg --import fleurdelix-signing-key.asc
gpg --fingerprint 0EEB9FE630C22E58
```

**2. Vérifier la signature**

```bash
gpg --verify SHA256SUMS.asc SHA256SUMS
```

Réponse attendue :

```
gpg: Bonne signature de « Fleurdelix OS <ddelaire@fleurdelix.quebec> »
```

L'avertissement `Cette clé n'est pas certifiée par une signature de
confiance` est normal : il signifie simplement que vous n'avez pas
personnellement attesté de notre identité. La signature est valide.

**3. Vérifier l'image**

```bash
sha256sum -c SHA256SUMS        # Linux
shasum -a 256 -c SHA256SUMS    # macOS
```

Réponse attendue :

```
fleurdelixOSCore-amd64-v20260322.iso: Réussi
```

### Sur Windows

Installez [Gpg4win](https://gpg4win.org/), puis dans PowerShell :

```powershell
gpg --import fleurdelix-signing-key.asc
gpg --verify SHA256SUMS.asc SHA256SUMS

Get-FileHash fleurdelixOSCore-amd64-v20260322.iso -Algorithm SHA256
```

Comparez l'empreinte obtenue avec le contenu de `SHA256SUMS`.

### Si la vérification échoue

**L'empreinte ne correspond pas** : le téléchargement est probablement
incomplet ou corrompu. Retéléchargez l'image.

**La signature est invalide** : ne l'installez pas. Signalez-le-nous.

### Ce que cette vérification prouve, et ne prouve pas

Elle prouve que l'image provient bien du détenteur de cette clé et qu'elle
n'a pas été modifiée depuis sa signature.

Elle ne remplace pas votre propre jugement sur le contenu de la
distribution, et elle n'a aucun lien avec le démarrage sécurisé (voir
ci-dessous).

---

### Démarrage sécurisé (Secure Boot)

Fleurdelix OS n'est pas signé pour le démarrage sécurisé. Cette
certification passe par un processus d'examen de plusieurs mois qui dépasse
les moyens actuels du projet.

**Désactivez le démarrage sécurisé dans le BIOS/UEFI avant de démarrer sur
la clé d'installation.** L'option se trouve en général sous *Security* ou
*Boot*, selon le fabricant.

Une fois le système installé, vous pouvez le réactiver si vous le souhaitez.

### Installation sur un PC, Mac, Machines Nvidia ou autres machines pouvant intégrer Linux

### Installation sur un environnement de machines virtuelles comme VirtualBox d'Oracle

- Installer VirtualBox d'oracle sous Windows, MacOs ou Linux Architecture Amd, intel
  - https://www.virtualbox.org/wiki/Downloads
 
- Créer une nouvelle machine virtuelle en spécifiant comme OS host Ubuntu ou Linux 64 avec un disque de stockage d'environ 30Gb
- Ajouter un média amovible pointant vers l'image Iso de Fleurdelix OS
- Puis booter sur l'image Live
- Vous pouvez utiliser le système tel quel mais il va être plus lent que si vous l'installer véritablement sur le disque de votre machine virtuelle.
- Pour cela, il suffit de double cliquer sur l'icône représentant un oeuf (Install System) :)

- Exemple d'écrans sur les étapes d'installation :
  - <img width="1347" height="886" alt="wwqeFYlD" src="https://github.com/user-attachments/assets/0c7ec2ee-4f56-43f8-8d75-6bed9e0d0666" />  
  - <img width="2048" height="840" alt="9k88pAVp" src="https://github.com/user-attachments/assets/eded0529-63bc-45e6-b8e3-061a520fca97" />
  - <img width="1357" height="776" alt="Xs7TyNZi" src="https://github.com/user-attachments/assets/8d358dee-7371-4502-8842-10bc9927394b" />
  - <img width="1365" height="823" alt="aIn_j_N9" src="https://github.com/user-attachments/assets/f18d5329-1db9-4e4e-b946-35221b7ed7f3" />
  - <img width="805" height="521" alt="YPM69Hnh" src="https://github.com/user-attachments/assets/d5b38c6f-39ea-4204-ac90-be150d3eede6" />
  - <img width="749" height="510" alt="jhM8ubNp" src="https://github.com/user-attachments/assets/67a4abff-856b-4792-9680-f34c9801f40b" />
  - <img width="745" height="496" alt="BsVIaHJO" src="https://github.com/user-attachments/assets/14a36f9c-2034-4e0d-b1d7-2afe17134e53" />
  - <img width="759" height="503" alt="avBtLXXK" src="https://github.com/user-attachments/assets/31dad93c-3dfc-4faf-a366-645d7afbe741" />
  - <img width="779" height="531" alt="Jj4cwbbO" src="https://github.com/user-attachments/assets/234a9f4e-9c55-472a-a1dd-50cbab8c63c3" />
  - <img width="770" height="506" alt="UI4k6Fpb" src="https://github.com/user-attachments/assets/7f325757-09d5-4852-93f0-a4e11f60846c" />
  








