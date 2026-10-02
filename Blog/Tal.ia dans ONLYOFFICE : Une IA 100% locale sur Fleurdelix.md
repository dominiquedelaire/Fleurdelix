---
title: "tal.ia dans ONLYOFFICE : une IA 100 % locale sur Fleurdelix"
description: "Comment intégrer un assistant IA qui tourne entièrement sur votre ordinateur dans ONLYOFFICE, grâce à Ollama et au modèle tal.ia."
date: 2026-09-26
Auteur : Dominique Delaire
---

# tal.ia dans ONLYOFFICE : une IA 100 % locale sur Fleurdelix

Résumer un texte, reformuler un courriel, trouver la bonne formule dans un tableur… L'IA peut vraiment nous simplifier la vie au bureau. Le hic, c'est que la plupart des assistants envoient vos documents sur des serveurs à l'autre bout du monde.

Dans ce tutoriel, on fait autrement : on utilise **tal.ia**, l'assistant de Fleurdelix, directement sur votre ordinateur, et on la branche dans **ONLYOFFICE**. Vos documents ne quittent jamais votre machine, et tout fonctionne même **sans connexion Internet**.

> **En bref :** Ollama fait tourner le modèle, tal.ia est notre version personnalisée du modèle dérivé de Qwen, et le plugin IA d'ONLYOFFICE fait le lien entre les deux.


## Introduction

Ollama et les modèles de Tal.ia, ainsi que OnlyOffice sont déjà installés dans Fleurdelix. Il n'est pas nécessaire d'installer autre chose.

Une carte graphique n'est pas obligatoire : le modèle fonctionne sur le processeur, simplement un peu plus lentement.

Par sécurité par défaut, Ollama refuse par défaut les requêtes venant d'applications comme ONLYOFFICE.

Comme Ollama tourne en tant que service, nous avons modifié sa configuration ainsi :

Dans notre config ollama.service :

```ini
[Service]
Environment="OLLAMA_ORIGINS=http://*,https://*,onlyoffice://*"
```

## Exemples d'utilisation dans OnlyOffice 





## Dépannage

**tal.ia n'apparaît pas dans la liste des modèles d'ONLYOFFICE**
Vérifiez qu'Ollama tourne (`systemctl status ollama`) et que le modèle existe (`ollama list`).

**C'est lent**
Sans carte graphique, c'est normal que la première réponse prenne quelques secondes. 

## À propos de tal.ia

tal.ia est une personnalisation du modèle dérivé de **Qwen3**, développé par l'équipe Qwen d'Alibaba Cloud et distribué sous licence **Apache 2.0**. Un grand merci à eux, ainsi qu'aux équipes d'Ollama et d'ONLYOFFICE, dont le travail ouvert rend ce genre de projet possible.
