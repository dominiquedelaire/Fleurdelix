[Accueil projet Fleurdelix](https://github.com/dominiquedelaire/Fleurdelix/blob/main/README.md)   

---
description: "Comment intégrer un assistant IA qui tourne entièrement sur votre ordinateur dans ONLYOFFICE, grâce à Ollama et au modèle tal.ia."
date: 2026-09-26
Auteur : Dominique Delaire
---

# tal.ia dans ONLYOFFICE : une IA 100 % locale sur Fleurdelix

Résumer un texte, reformuler un courriel, trouver la bonne formule dans un tableur… L'IA peut vraiment nous simplifier la vie au bureau. Le hic, c'est que la plupart des assistants envoient vos documents sur des serveurs à l'autre bout du monde.

Dans ce tutoriel, on fait autrement : on utilise **tal.ia**, l'assistant de Fleurdelix, directement sur votre ordinateur, et on la branche dans **ONLYOFFICE**. Vos documents ne quittent jamais votre machine, et tout fonctionne même **sans connexion Internet**.

> **En bref :** Ollama fait tourner le modèle, tal.ia est notre version personnalisée du modèle dérivé de Qwen, et le plugin IA d'ONLYOFFICE fait le lien entre les deux.

<img width="1254" height="1254" alt="onlyoffice talia" src="https://github.com/user-attachments/assets/f437de71-dac3-4712-b216-1ac92efb3f7a" />


## Introduction

Ollama et les modèles de Tal.ia, ainsi que OnlyOffice sont déjà installés dans Fleurdelix. Il n'est pas nécessaire d'installer autre chose.

Une carte graphique n'est pas obligatoire : le modèle fonctionne sur le processeur, simplement un peu plus lentement.

Par sécurité, Ollama refuse par défaut les requêtes venant d'applications comme ONLYOFFICE.

Comme Ollama tourne en tant que service, nous avons modifié sa configuration ainsi :

Dans notre config ollama.service :

```ini
[Service]
Environment="OLLAMA_ORIGINS=http://*,https://*,onlyoffice://*"
```

## Exemples d'utilisation dans OnlyOffice 

Voici 2 exemples, le premier dans le traitement de texte et le deuxième dans le tableur :

Dans ONLYOFFICE, allez dans l'onglet IA (s'il n'est pas présent, activer le module dans "Modules complémentaires". 
Puis choisir 'Paramètres'. On va ajouter les modèles Tal.ia de Fleurdelix OS dans OnlyOffice. 
Choisir "Modifier les modèles d'IA"

<img width="1971" height="1198" alt="Screenshot_20260930_221442" src="https://github.com/user-attachments/assets/e0e3da87-48a3-48a8-9028-f74cec0cce30" />

Puis cliquer sur le bouton "+"   

<img width="1576" height="1029" alt="Screenshot_20260930_221514" src="https://github.com/user-attachments/assets/f287adfb-2476-4644-9b8f-2ec96e38e112" />

Choisir **Ollama** comme Fournisseur de modèle, puis ensuite dans les modèles, choisir **Tal.Ia légère** puis cliquer sur le bouton 'OK'
<img width="1576" height="1029" alt="Screenshot_20260930_224917" src="https://github.com/user-attachments/assets/390bfdb2-99b5-4756-a269-4364da14b382" />

Faire la même chose en ajoutant aussi le modèle Tal.ia standard   
<img width="446" height="438" alt="image" src="https://github.com/user-attachments/assets/72a0b719-f027-4e83-b5ee-1301eed280b9" />   

Ensuite vous pouvez affecter le modèle tal.ia légère ou tal.ia standard aux différentes catégories :    
<img width="451" height="588" alt="image" src="https://github.com/user-attachments/assets/fd5d570e-4ba3-4189-b185-939ff2a18965" />   


Ouvrir un document ou écrire un texte et sélectionner le paragraphe puis bouton droit puis fonction **Réécrire différemment** de la fonction **Analyse de texte** de la fonction IA :    
<img width="1576" height="1029" alt="Screenshot_20260930_232733" src="https://github.com/user-attachments/assets/a65e354a-677d-4eb0-9721-0643e16cad96" />   


Après quelques secondes de traitement   
<img width="1576" height="1029" alt="Screenshot_20260930_232849" src="https://github.com/user-attachments/assets/402d1f76-3968-4dc2-b9bb-ac82fb3bc336" />

Le texte a été réécrit avec l'utilisation du modèle local tal.ia légère :) Cela fonctionne complètement en local. Vous pouvez essayer aussi en coupant le réseau ou internet :)   
<img width="1576" height="1029" alt="Screenshot_20260930_233000" src="https://github.com/user-attachments/assets/b14448a2-5643-40e4-bcc4-fffdda5dfed9" />   

Deuxième exemple simple en créant un nouveau classeur excel :   
<img width="1576" height="1029" alt="Screenshot_20260930_233858" src="https://github.com/user-attachments/assets/3ce094d5-880a-4c2e-8c7b-3e91360f35e6" />

Saisir des chiffres ou un petit tableau pour tester la génération de formules par exemple :  
Cliquer sur 'Chatbot' de l'onglet IA puis saisir un prompt pour demander une formule de calcul sur un élément précis :   
<img width="1576" height="1029" alt="Screenshot_20260930_234133" src="https://github.com/user-attachments/assets/cec10d48-9258-432c-998f-0986a4d8a0d2" />   

On attend quelques secondes   
<img width="1576" height="1029" alt="Screenshot_20260930_234208" src="https://github.com/user-attachments/assets/f16173cf-0559-4347-ad78-188dc8f6cb6f" />

Et on obtient le résultat
<img width="1576" height="1029" alt="Screenshot_20260930_235514" src="https://github.com/user-attachments/assets/7c9d5304-df38-45f9-9d7e-2cb74e6cea2f" />


## Dépannage

**tal.ia n'apparaît pas dans la liste des modèles d'ONLYOFFICE**   
Vérifiez qu'Ollama tourne (`systemctl status ollama`) et que le modèle existe (`ollama list`).

**C'est lent**   
Sans carte graphique, c'est normal que la première réponse prenne quelques secondes. 

## À propos de tal.ia

tal.ia est une personnalisation du modèle dérivé et entraîné de **Qwen3**, développé par l'équipe Qwen d'Alibaba Cloud et distribué sous licence **Apache 2.0**. Un grand merci à eux, ainsi qu'aux équipes d'Ollama et d'ONLYOFFICE, dont le travail ouvert rend ce genre de projet possible.


---

*Fleurdelix OS · Souverain · Libre · Pour demain*
