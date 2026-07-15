**Titre :** Construction de la base du noyau de Fleurdelix OS   
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
  - sudo adduser fleurdelix-admin
  - sudo usermod -aG sudo fleurdelix-admin
- sudo apt update
- sudo apt install --no-install-recommends xorg xfce4 lightdm python3-pip python3-venv
- Commande pour désactiver les messages publicitaires d'Ubuntu     
  - sudo chmod -x /etc/update-motd.d/*
- Install de nano editeur : sudo apt install nano -y
- Pour ajouter le nom fleurdelix à la connexion : sudo nano /etc/issue (Modifier texte par Fleurdelix 2026.03.22
- sudo apt update && sudo apt upgrade -y
- Si votre machine a un driver Nvidia : sudo ubuntu-drivers install (si l'installation et la création de Fleurdelix se fait dans une machine virtuelle ou VM, sous une machine physique Nvidia, ce n'est pas nécessaire)
- Installation de l'écran de connexion : sudo apt install lightdm slick-greeter lightdm-settings --no-install-recommends -y
- Activation et nettoyage : sudo systemctl set-default graphical.target
- Préparation des répertoires fleurdelix pour les ressources graphiques, images, icones et autres ressources
  - sudo mkdir -p /usr/share/fleurdelix/ressources/logos
 
Finir Documentation  

# Construction sur architecture Arm (Raspberry, Mac Studio, Nouveaux mac avec puces Mx, Majorité de téléphones Android, Aws Graviton, Azure, Nvidia Jetson, et autres architectures Arm)
