# Guide d’utilisation

Niak Confort dit, pour chaque pièce, quoi faire et pourquoi. Ce guide explique comment le régler et comment lire ses conseils.

- [Premiers pas](#premiers-pas)
- [L’extérieur](#lextérieur)
- [Les pièces](#les-pièces)
- [Lire les conseils](#lire-les-conseils)
- [Fenêtres, chauffage, VMC, purificateur, volets](#fenêtres-chauffage-vmc-purificateur-volets)
- [Chaque pièce apprend](#chaque-pièce-apprend)
- [Pour vos automatisations](#pour-vos-automatisations)

Un souci ? Voir le [dépannage](depannage.md).

## Premiers pas

1. Installez **Niak Comfort** depuis HACS, puis redémarrez Home Assistant ([installation](../README.md#installation)).
2. **Paramètres → Appareils et services → Ajouter une intégration → Niak Comfort.**
3. Ouvrez **Niak** dans la barre latérale, onglet **Confort**.
4. Niak propose toutes les pièces où il trouve une température. Décochez celles à ne pas suivre, puis créez-les d’un coup.
5. Réglez l’extérieur une fois, dans **Réglages généraux**.
6. Ajoutez la carte à un tableau de bord : **Ajouter une carte → Niak Confort**.

Seule la température de la pièce est obligatoire. Chaque capteur ajouté rend les conseils plus justes.

Rien n’est enregistré avant **Enregistrer**. Vous pouvez revenir à chaque onglet avant.

## L’extérieur

L’extérieur se règle une seule fois, dans **Confort → Réglages généraux**. Il sert à toutes les pièces.

### Avec Niak Weather

Si [Niak Weather](https://github.com/Niakman13/niak-weather-integration) est installé, choisissez **Niak Weather** puis votre lieu.

Confort reprend alors :

- la station de votre lieu : température, humidité, pluie, vent, soleil ;
- les prévisions : « Refermez avant la pluie », « Aérez vers 22 h », fraîcheur de la nuit ;
- les vigilances et les orages ;
- la qualité de l’air du jour.

L’air du dehors suit la source choisie dans Niak Weather : Atmo France ou une station WAQI. Changez-la dans Weather : Confort suit. Il faut Niak Weather 2.5.7 ou plus récent.

### Avec vos propres capteurs

Choisissez **Vos propres capteurs**, puis chaque mesure. Toutes sont facultatives :

| Mesure | À quoi elle sert |
| --- | --- |
| Température et humidité | Savoir si l’air du dehors rafraîchit ou assèche |
| Pluie (en mm/h, la pluie en cours) | Faire refermer les fenêtres exposées |
| Rafales | Ne rien laisser ouvert par vent fort |
| Direction du vent | Dire quelles fenêtres ouvrir pour faire traverser l’air |
| Ensoleillement (W/m²) | Repérer le soleil qui chauffe une façade |
| Qualité de l’air | Éviter d’aérer quand l’air du dehors est mauvais |

Pour la qualité de l’air, trois choix : **Atmo France**, l’indice de **Niak Weather**, ou aucune.

L’indice du jour est une précaution. Il ne mesure pas l’air devant vos fenêtres.

Une mesure absente reste inconnue : Niak conseille quand même et le dit sur la carte.

## Les pièces

La **vue d’ensemble** liste vos pièces. **Configurer** ouvre les réglages d’une pièce.

![Les réglages d’une pièce : l’onglet Ouvertures](images/niak-comfort-reglages.png)

Une pièce peut être :

- **rattachée à une pièce Home Assistant** : Niak propose ses capteurs ;
- **libre** : « Étage », « Suite parentale »… Vous choisissez les capteurs.

Les pièces extérieures (Jardin, Terrasse…) ne sont pas proposées comme pièces.

Chaque pièce a six onglets. Le cadre **À quoi sert cette étape ?** explique chacun.

### Température

- La température : la seule mesure obligatoire.
- L’humidité : facultative, elle repère un air trop humide.
- Votre plage de confort : 20 à 24 °C l’hiver, jusqu’à 26 °C l’été par défaut.
- La plage d’été arrive en douceur, quand les 7 derniers jours se réchauffent.
- Le seuil d’humidité haute : 60 % par défaut.

### Ouvertures

Pour chaque fenêtre ou porte qui donne dehors :

- son contact (ouvert ou fermé) ;
- son exposition : N, NE, E, SE, S, SO, O, NO ;
- son type : fenêtre, porte-fenêtre, vasistas, porte ;
- s’il est abrité par une avancée de toit ou un balcon ;
- son volet : aucun, manuel ou connecté ([les volets](#volets)).

Les dimensions sont facultatives. Elles affinent l’ombre et la durée d’aération.

### Air intérieur

Tout est facultatif :

- **CO₂** : aérer ferait du bien à 800 ppm, aérer à 1 000, attention à 1 500.
- **Particules fines PM2.5** : signalement à 15 µg/m³.
- **COV** : un seuil seulement si votre capteur est reconnu (indice 150 pour une IKEA VINDSTYRKA).
- **Purificateur** et **Ventilation (VMC)**, avec sa grande vitesse si elle en a une.

Chaque seuil est expliqué avec ses sources : [les repères](SEUILS.md).

### Présence

Des détecteurs de présence ou de mouvement, facultatifs.

Une pièce vide adapte ses conseils. Son suivi continue : une fenêtre ouverte reste signalée.

Un détecteur de mouvement silencieux ne prouve pas que la pièce est vide. Délai avant de la considérer vide : 5 minutes par défaut.

### Chauffage

Le thermostat ou la vanne de la pièce.

Niak sait alors si le chauffage tourne. Il évite de conseiller d’ouvrir pendant qu’il chauffe.

Il ne commande rien.

### La pièce

- Le nom de la pièce et sa pièce Home Assistant.
- L’étage : repris de Home Assistant, ou à choisir pour une pièce libre.
- **Pièce non chauffée** : Niak ne conseille jamais de la réchauffer.
- Les réglages avancés, facultatifs : rafales (45 km/h), gel (1 °C), soleil sur une façade (250 W/m²), faible lumière (100 lux), ancienneté des mesures (3 h).

Un capteur à vérifier demande une confirmation. Elle est retenue ensuite.

## Lire les conseils

### La carte d’une pièce

**En haut, le conseil.** Quelques mots, puis la raison chiffrée :

> **Aérez 25 à 35 min**
> Dehors 78 %, mais l’air froid contient peu d’eau : environ 63 % après l’aération.

À droite, un pictogramme. En dessous, la fenêtre à ouvrir.

**La couleur** dit s’il y a quelque chose à faire :

| Couleur | Étiquette | Sens |
| --- | --- | --- |
| Bleu | Tout va bien | Rien à faire |
| Vert | À saisir | Un bénéfice, souvent plus tard : « Aérez vers 23 h » |
| Orange | Geste conseillé | Un geste utile maintenant |
| Rouge | Attention | Urgent : « Fermez, il pleut » |
| Gris | — | Mesures en chargement, absentes ou incomplètes |

Niak ne parle que pour un geste qui aide. Sinon : « Rien à faire ».

Plusieurs conseils ? Ils défilent, le plus important d’abord. Un appui passe au suivant.

**Pendant l’aération**, le conseil suit le temps : « Encore 5 min d’aération », puis « Vous pouvez refermer ».

**L’échelle de température** place la pièce dans votre plage :

- la bande bleue : votre plage du jour ;
- le trait sombre : le minimum et le maximum des dernières 24 h ;
- le rond vide : la température dehors.

**Les mesures** sont des tuiles : humidité, CO₂, fenêtres, soleil, chauffage, VMC… Une mesure hors de votre plage s’encadre en ambre.

**Détails** rassemble les sources, la tendance, l’apprentissage (« Séchage ») et ce qui manque.

Un appui sur une tuile de mesure ouvre son historique dans Home Assistant. Le bouton **i** explique le conseil.

### La carte du logement

- Les conseils de toutes les pièces, le plus urgent d’abord, avec le nom de la pièce.
- Une échelle avec un point par pièce.
- **Pièces** : la température et le geste de chaque pièce.
- **Détails** : par où commencer pour rafraîchir, l’air qui traverse, l’écart entre étages, le soleil qui entre.

Avec des étages Home Assistant, les pièces sont regroupées par étage. De plain-pied, tout est dans **Mon logement**.

Niak peut proposer deux fenêtres à ouvrir ensemble :

- sur deux façades opposées : l’air traverse ;
- sur deux étages : effet cheminée, même sans vent.

Il suppose que l’air passe librement entre les pièces. Il ne garantit pas le courant d’air.

### Choisir un format

Dans l’éditeur de la carte, choisissez d’abord le format.

Carte d’une pièce :

| Format | Ce qu’il montre |
| --- | --- |
| Complète | Le conseil, l’échelle, les mesures et les détails |
| Tuile | Le conseil et ses pastilles ; elle se déplie d’un appui |
| Tuile dépliée | La même, ouverte au départ |
| Mini | Une ligne : le conseil et la température |
| Mesures | Les tuiles de la pièce, sans conseil |
| Alerte | Visible seulement quand un geste est conseillé |

Carte du logement : complète, tuile, liste des pièces, mini ou alerte.

Un appui long sur une tuile ouvre la carte complète en fenêtre, une page de votre choix, ou rien. Sur mini et alerte, un simple appui suffit.

Ensuite, des groupes repliables, qui changent avec le format : visuel et animations, bandeau, échelle, mesures, détails. Le contenu du bandeau, les pastilles et les rubriques se cochent et s’ordonnent.

La carte suit le thème de Home Assistant, clair ou sombre.

## Fenêtres, chauffage, VMC, purificateur, volets

Niak observe vos équipements. Il ne les commande jamais.

### Fenêtres

- Une fenêtre qui s’ouvre apparaît sur la carte en une à deux secondes.
- Le conseil attend 30 secondes, pour ignorer un contact qui rebondit.
- **Pluie** : Niak fait fermer les ouvrants exposés. Ceux qui sont abrités peuvent rester ouverts.
- **Vent fort** : au-delà de 45 km/h de rafales, rien ne reste ouvert.
- **Gel** : pas d’aération prolongée sous 1 °C.
- **Soleil** : Niak signale la fenêtre ouverte par laquelle le soleil chauffe la pièce.
- Avec le vent, il dit quelles fenêtres ouvrir pour faire traverser l’air.

### Chauffage

- La tuile Chauffage montre s’il chauffe, et son mode (hors gel, éco, confort…).
- Pendant qu’il chauffe, Niak limite l’aération.
- Un CO₂ élevé garde une aération courte : l’air doit quand même être renouvelé.

### VMC

- La tuile Ventilation dit si elle tourne, et si elle est en grande vitesse.
- Quand ouvrir la fenêtre sécherait peu, Niak propose plutôt : « Lancez la VMC ».

### Purificateur

- Il filtre les particules : un purificateur en marche est un remède en cours.
- Il ne retire pas le CO₂ : l’aération reste conseillée si le CO₂ monte.

### Volets

Chaque ouvrant peut avoir :

- **aucun volet** ;
- **un volet manuel** (bois, battant…) : Niak ne connaît pas sa position. Il conseille sous condition : « Si le volet est ouvert, fermez-le côté ouest » ;
- **un volet connecté** : Niak lit sa position, et son automatisme ou sa dérogation si vous les choisissez.

En été, Niak conseille de protéger les façades au soleil. En hiver, il signale le soleil qui peut chauffer.

Avec une avancée de toit et ses dimensions, l’ombre est estimée. Sans dimensions, un modèle simple est utilisé.

## Chaque pièce apprend

Une aération ne remplace jamais tout l’air. Chaque pièce sèche à sa façon.

Niak relit les ouvertures des 10 derniers jours. Il retient, pour chaque pièce :

- à quelle vitesse elle sèche ;
- l’humidité qui reste ;
- l’humidité qui revient après la fermeture.

Les nouvelles aérations s’ajoutent ensuite, jusqu’à 90 jours.

Ce que ça change :

- **Une promesse réaliste** : « 76 % d’humidité, environ 70 % après l’aération ».
- **La durée de la pièce** : 20 min dans une buanderie qui sèche vite, une heure dans une chambre qui sèche mal.
- **Pas de geste inutile** : si aérer ne gagne presque rien, Niak ne le demande pas. Il propose la VMC si la pièce en a une.
- **Le bon moment** : « Aérez vers 22 h » quand l’air du soir sera plus sec (avec Niak Weather).

Dans **Détails**, la ligne **Séchage** dit sur combien d’aérations la pièce a appris.

Pour apprendre, une pièce a besoin :

- d’un contact de fenêtre ;
- de sa température et de son humidité ;
- de la température et de l’humidité du dehors ;
- de l’historique de Home Assistant (l’enregistreur, actif par défaut).

Une ouverture de moins de 10 minutes ne compte pas. Avant d’avoir appris, Niak suppose une pièce ordinaire, avec prudence.

## Pour vos automatisations

Chaque pièce crée cinq entités, rattachées à son appareil :

| Entité | Valeurs |
| --- | --- |
| **Situation** | Tout va bien · Potentiel détecté · Geste conseillé · Attention nécessaire · Information incomplète |
| **Geste** | Ouvrir · Fermer · Attendre · Aucun nouveau geste · À vérifier |
| **Raison** | Dans la plage de confort · Pluie et ouvrants ouverts · Renouvellement d’air nécessaire · Rafraîchissement possible · Assèchement possible · Soleil qui entre · Pluie imminente… |
| **Chauffage observé** | Chauffe en cours · Au repos · Arrêté · Rafraîchit · Inconnu · Non configuré |
| **Couverture des données** | Sources configurées disponibles · Bilan partiel |

Leur nom suit celui de la pièce, par exemple `sensor.salon_geste`.

Exemples :

- prévenir quand le **Geste** d’une pièce passe à **Fermer** et que la **Raison** est la pluie ;
- allumer un voyant quand la **Situation** passe à **Attention nécessaire** ;
- couper un chauffage d’appoint quand le **Geste** devient **Ouvrir**. Cette décision reste la vôtre : Niak ne commande rien.
