# Construction de la base du noyau de Fleurdelix OS   
**Auteur :** Dominique Delaire   
**Date de création initiale :** 14 juin 2025   
**Date de mise à jour :** 15 juillet 2026     

Le mode opératoire suivant permet de construire le noyau de base de l'OS Fleurdelix pour différentes architectures   


# Construction sur architecture Version PC Intel / Amd, Imac, Mac book, Mac book pro processeur Intel
## Installation
### Téléchargement du noyau Ubuntu server 26.04 LTS minimal 
- Télécharger le Iso sur le site officiel (sans logiciel, sans base, sans interface graphique, juste le noyau)
- Créer une clé Usb bootable avec le iso
- Booter avec la clé Usb et installer sur votre machine, Ubuntu Server 26.04 LTS la version minimale sans aucun logiciel. Connecter juste votre serveur au wifi en suivant les instructions lors de l'installation

### Configuration du noyau
- Création du user "fleurdelix-admin" avec le mot de passe "quebec" :   
  - **sudo adduser fleurdelix-admin**
  - **sudo usermod -aG sudo fleurdelix-admin**
- **sudo apt update**
- **sudo apt install --no-install-recommends xorg xfce4 lightdm python3-pip python3-venv**
- Commande pour désactiver les messages publicitaires d'Ubuntu     
  - **sudo chmod -x /etc/update-motd.d/***
- Install de nano editeur : **sudo apt install nano -y**
- Pour ajouter le nom fleurdelix à la connexion : **sudo nano /etc/issue** (Modifier texte par Fleurdelix 2026.03.22)
- **sudo apt update && sudo apt upgrade -y**
- Si votre machine a un driver Nvidia : **sudo ubuntu-drivers install** (si l'installation et la création de Fleurdelix se fait dans une machine virtuelle ou VM, sous une machine physique Nvidia, ce n'est pas nécessaire)
- Installation de l'écran de connexion : **sudo apt install lightdm slick-greeter lightdm-settings --no-install-recommends -y**
- Activation et nettoyage : **sudo systemctl set-default graphical.target**
- Préparation des répertoires fleurdelix pour les ressources graphiques, images, icones et autres ressources
  - **sudo mkdir -p /usr/share/fleurdelix/ressources/logos**
- Installation ensuite de l'environnement graphique Kde Plasma, très bon environnement graphique, c'est ce que nous avons privilégié pour Fleurdelix :
  - **sudo apt install kde-standard -y** (A l'installation, le système va demander le "display manager" : choisir sddm (celui de KDE)
  - Pourquoi nous avons choisi sddm : il est plus beau pour KDE, il permet des thèmes animés, des vidéos en fond d'écran de login, etc..
- Redémarrer : **sudo reboot**
- A l'écran de connexion au reboot, choisir en bas à gauche ou à droite sur la roue dentée, soit Plasma, soit Wayland (Avec Nvidia, wayland est plus compatible mais pas de pb majeur non plus avec plasma)
- On va maintenant ajouter des élements à l'interface du bureau :
  - Sur le bureau, faire "Bouton droit de la souris" en bas et choisir l'option "Enter Edit Mode", puis "Add Panel" et choisir "Application menu bar"
  - Ensuite sur "Enter Edit Mode" toujours, choisir "Add or manage widget" et choisir "Application Dashboard".
- On va nettoyer ensuite l'installation de notre premier display manager en faisant : **sudo apt purge lightdm -y puis sudo apt autoremove --purge -y**
- On va réparer les éventuels "trous" KDE par expérience :) : **sudo apt install kde-standard network-manager-gnome konsole dolphin -y**
- Ensuite on va installer notre premier navigateur web chromium (on installera firefox plus tard) : **sudo apt install chromium-browser**
- On va aussi débuter la personnalisation au fur et à mesure :
  - Faire un clic droit sur l'icone en bas à gauche de KDE puis l'option "Configurer le lanceur d'application" puis cliquer sur l'icone pour choisir la ressource fleurdelix-logo.png dans /usr/share/fleurdelix/fleurdelix-logo.png
  - A documenter : Complèter avec l'écran de démarrage et le fond d'écran.
  - On va modifier aussi dans la séquence de boot et d'autres éléments avec le système officiel modifié soit bien Fleurdelix et non Ubuntu Server, puisque Fleurdelix est une distribution spécifique avec des logiciels et frameworks spécifiques
  - **sudo nano /etc/os-release** :
    - Modifier les lignes suivantes et remplacer le nom ubuntu par Fleurdelix (garder juste la propriété ID_LIKE=Ubuntu ou ce qui y ressemble)
      - PRETTY_NAME="Fleurdelix 2026.03.22"
      - NAME="Fleurdelix"
      - VERSION_ID="26.03.22"
      - VERSION="26.03.22 (Core)"
      - ID=fleurdelix
      - HOME_URL="https://github.com/dominiquedelaire/Fleurdelix"
      - SUPPORT_URL="https://github.com/dominiquedelaire/Fleurdelix"
      - BUG_REPORT_URL="https://github.com/dominiquedelaire/Fleurdelix"
      - PRIVACY_POLICY_URL="https://github.com/dominiquedelaire/Fleurdelix"
      - LOGO=fleurdelix-logo
    - On sauvegarde avec Ctrl+O , Entrée puis Ctrl+X
  - On va modifier aussi la compatibilité héritée
    - **sudo nano /etc/lsb-release**
      - Modifier les lignes suivantes par :
        - DISTRIB_ID=Fleurdelix
        - DISTRIB_RELEASE=26.03.22
        - DISTRIB_DESCRIPTION="Fleurdelix 26.03.22 (Core)"
      - Sauvegarder et quitter
  - On va maintenant changer le nom au démarrage de la machine (GRUB)
    - **sudo nano /etc/default/grub**
      - Modifier la ligne suivante par :
        - GRUB_DISTRIBUTOR="Fleurdelix"
      - Sauvegarder et quitter
    - On met à jour le menu de démarrage de l'OS pour appliquer le changement : **sudo update-grub**
  - On reboot pour valider les changements : **sudo reboot**  


# Construction sur architecture Arm (Raspberry, Mac Studio, Nouveaux mac avec puces Mx, Majorité de téléphones Android, Aws Graviton, Azure, Nvidia Jetson, et autres architectures Arm)
