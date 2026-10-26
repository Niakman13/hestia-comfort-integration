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

Confort reprend alors, sans rien à choisir :

- la station de votre lieu : température, humidité, pluie, vent, soleil ;
- les prévisions : « Refermez avant la pluie », « Aérez vers 22 h », fraîcheur de la nuit ;
- les vigilances et les orages ;
- la qualité de l’air du jour.

Les mesures sont seulement affichées, avec leur valeur du moment. Pour en changer : changez la station dans Niak Weather, ou choisissez **Vos propres capteurs**.

L’air du dehors suit la source choisie dans Niak Weather : Atmo France ou une station WAQI. Changez-la dans Weather : Confort suit. Il faut Niak Weather 2.5.7 ou plus récent. Dans Confort, seul le niveau de prudence se règle. Pour ne pas tenir compte de l’air, désactivez la qualité de l’air dans Niak Weather.

### Avec vos propres capteurs

Choisissez **Vos propres capteurs**, puis le capteur de chaque mesure ; sa valeur du moment s’affiche à côté. Toutes sont facultatives :

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

L’accueil Confort (**Vue d’ensemble**) liste vos pièces : leurs mesures, leur apprentissage et un bouton **Modifier**, qui ouvre les réglages de la pièce. **Ajouter une pièce** propose vos pièces Home Assistant pas encore suivies, ou une pièce libre.

![Les réglages d’une pièce : l’onglet Ouvertures](images/niak-comfort-reglages.png)

### Niak part de vos pièces Home Assistant

Vous avez déjà rangé vos appareils par pièce dans Home Assistant ? Niak s’en sert. Presque tout est prérempli.

- **Les pièces** : Niak propose chaque pièce Home Assistant qui a un thermomètre. Vous cochez, il les crée d’un coup.
- **Les capteurs** : pour chaque mesure, il propose ceux de la pièce. Un capteur compte s’il est rangé dans la pièce, lui ou son appareil.
- **La température et l’humidité de la pièce** : si vous les avez choisies dans Home Assistant, Niak les prend en premier.
- **L’étage** : celui de la pièce dans Home Assistant.

Vous vérifiez, vous gardez, vous changez. Rien n’est choisi sans vous.

Plusieurs capteurs possibles ? Niak les montre tous et vous choisissez.

Un capteur d’une autre pièce, ou d’un appareil dehors, demande une confirmation.

Un capteur mal rangé ? Corrigez sa pièce dans Home Assistant : Niak le proposera au bon endroit. Vous pouvez aussi choisir n’importe quel capteur avec le sélecteur de Home Assistant.

Une pièce ajoutée plus tard dans Home Assistant apparaît dans **À améliorer** : « Bureau pas encore suivie ».

Niak ne devine rien d’un nom : il suit le rangement de Home Assistant et la nature des capteurs.

### Pièce libre

Une pièce sans pièce Home Assistant : « Étage », « Suite parentale »… Vous choisissez les capteurs et, si besoin, l’étage.

Les pièces extérieures (Jardin, Terrasse…) ne sont pas proposées comme pièces.

### Six onglets par pièce

Chaque pièce a six onglets, détaillés ci-dessous. Le cadre **À quoi sert cette étape ?** explique chacun.

### Température

- La température : la seule mesure obligatoire.
- L’humidité : facultative, elle repère un air humide ou sec.
- Votre plage de confort : 20 à 24 °C l’hiver, jusqu’à 26 °C l’été par défaut.
- La plage d’été arrive en douceur, quand les 7 derniers jours se réchauffent.
- La plage d’humidité : minimum 40 % et maximum 60 % proposés, réglables pour chaque pièce. Le maximum déjà choisi est conservé.

Un écart jusqu’à 3 points reste discret : « Légèrement humide » ou « Légèrement sec », sans compter la pièce parmi celles à surveiller pour ce seul écart. Entre 3 et 10 points, la carte indique « Air humide » ou « Air sec » ; au-delà de 10 points, « Très humide » ou « Très sec ». Ce sont des paliers d’affichage Niak, pas des seuils sanitaires. À 60,6 % avec un maximum de 60 %, la carte indique donc « Légèrement humide ».

L’état affiché suit la mesure actuelle, même après une humidité plus élevée. Une amélioration et un écart durable sont précisés dans « À savoir ». Le conseil reste lié à un geste utile : ouvrir n’est pas conseillé pour un léger dépassement seul, et un risque estimé sur les murs froids reste expliqué séparément. Pour un air sec, la carte précise si l’air extérieur assécherait davantage ou pourrait augmenter l’humidité ; sans mesure extérieure, elle ne suppose aucun effet.

### Ouvertures

Pour chaque fenêtre ou porte qui donne dehors :

- son contact (ouvert ou fermé) ;
- son exposition : N, NE, E, SE, S, SO, O, NO ;
- son type : fenêtre, porte-fenêtre, vasistas, porte ;
- s’il est abrité par une avancée de toit ou un balcon ;
- son volet : aucun, manuel ou connecté ([les volets](#volets)).

Les dimensions sont facultatives. Elles affinent l’ombre et la durée d’aération.

Pas de contact dans une pièce, et c’est voulu (un garage, une pièce jamais aérée) ? Cochez **Pas de contact de fenêtre ici, c’est voulu** : la suggestion « ouvrants non mesurés » disparaît pour cette pièce.

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

Un détecteur de mouvement silencieux ne prouve pas que la pièce est vide. Délai avant de la considérer vide : 5 minutes par défaut. Pendant ce délai, la carte dit « personne depuis 3 min ».

**Personnes de la pièce** : cochez les personnes de Home Assistant à qui sert la pièce. Une pour une chambre, plusieurs pour une pièce commune. La pièce compte comme vide quand elles sont toutes absentes, même si d’autres sont à la maison : pas de « Rallumez le chauffage » dans la chambre de quelqu’un qui est parti, et un avertissement si sa fenêtre est restée ouverte. Sans case cochée, toute la maison compte.

**Alarme** (Réglages généraux) : Alarmo est reconnu tout seul ; vous pouvez choisir une autre alarme, ou aucune. Armée en absence ou en vacances, la maison est vide, et une fenêtre ouverte devient urgente : « Refermez ». En mode nuit, une fenêtre ouverte est signalée, sauf celle que vous avez dit laisser ouverte exprès pour dormir au frais.

### Chauffage

Le thermostat ou la vanne de la pièce.

Niak sait alors si le chauffage tourne. Il évite de conseiller d’ouvrir pendant qu’il chauffe.

**Quand conseiller de rallumer** : sous le minimum de la pièce, Niak le dit d’abord dans « À savoir ». « Rallumez le chauffage » n’apparaît que si la pièce reste plus bas que la **tolérance** (1 °C par défaut, de 0 à 5 °C) pendant 30 minutes, avec quelqu’un à la maison et le chauffage coupé, et qu’elle ne se réchauffe pas d’elle-même (le soleil, par exemple).

Un thermostat qui ne dit pas ce qu’il fait (sans « action » dans Home Assistant) est au moins lu « coupé » quand son mode est arrêt.

**Avec Versatile Thermostat**, reconnu tout seul, l’onglet montre ses consignes et propose de prendre sa **consigne comme minimum** de la pièce (coché par défaut) : le minimum suit ce que le thermostat vise, en confort ou en éco. Une pièce à 18 °C quand il vise 17 °C en éco n’est donc pas « trop fraîche ». Le hors-gel protège sans être un confort : la température confort reste alors le minimum, mais Niak ne demande pas de rallumer. Niak lit aussi :

- pourquoi il est arrêté : seul un arrêt à la main appelle « Rallumez ». Arrêté par une fenêtre ouverte, par son arrêt automatique, un mode central ou un délestage, il repartira seul : la carte l’explique ;
- son préréglage : en éco, hors-gel ou absence, une pièce plus fraîche est voulue, Niak ne demande pas de rallumer ;
- la pente de la température, tant que le jumeau de la pièce apprend ;
- la présence ou le mouvement qu’il suit, pour une pièce sans détecteur à elle ;
- la fenêtre ouverte qu’il détecte, dite dans « À savoir » quand aucun contact de la pièce ne le dit.

Il ne commande rien.

### La pièce

- Le nom de la pièce et sa pièce Home Assistant.
- L’étage : repris de Home Assistant, ou à choisir pour une pièce libre.
- **Pièce non chauffée** : Niak ne conseille jamais de la réchauffer.
- **Même air** : cochez les pièces ouvertes sur celle-ci, sans mur ni porte entre elles (un salon ouvert sur sa cuisine). Leurs fenêtres comptent pour les deux, elles n’ont qu’une carte, et jamais deux gestes contraires.
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

**Dessous, « À savoir »** : ce qui est utile à savoir, sans geste à faire. Une idée par ligne : risque de moisissure sur les murs froids, air humide dehors, même air qu’une autre pièce, VMC en marche, résultat de la dernière aération (« humidité 76 → 70 % »).

Plusieurs conseils ? Ils défilent, le plus important d’abord. Un appui passe au suivant.

**Pendant l’aération**, le conseil suit le temps : « Encore 5 min d’aération », puis « Vous pouvez refermer ».

**L’échelle de température** place la pièce dans votre plage :

- la bande bleue : votre plage du jour ;
- le trait sombre : le minimum et le maximum des dernières 24 h ;
- le rond vide : la température dehors.

**Les mesures** sont des tuiles : humidité, CO₂, fenêtres, soleil, chauffage, VMC… Une mesure hors de votre plage n’est encadrée en ambre que si un geste est conseillé.

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
| Complète | Le bandeau conseil (avec l’échelle et le graphique), À savoir, les mesures et les détails techniques |
| Tuile | Le conseil et ses pastilles ; elle se déplie d’un appui |
| Tuile dépliée | La même, ouverte au départ |
| Mini | Une ligne : le conseil et la température |
| Mesures | Les tuiles de la pièce, sans conseil |
| Alerte | Visible seulement quand un geste est conseillé |

Carte du logement : complète, tuile, liste des pièces, mini ou alerte.

Un appui long sur une tuile ouvre la carte complète en fenêtre, une page de votre choix, ou rien. Sur mini et alerte, un simple appui suffit.

Ensuite, les réglages suivent les quatre sections de la carte, numérotées dans le même ordre :

1. **Bandeau conseil** : faire défiler les conseils, ce qui défile après le conseil (équipements en marche, meilleur moment plus tard), les repères de l’échelle de température, et le **graphique « Prochaines heures »** avec ses sujets (température, humidité).
2. **À savoir** : afficher ou non, les sujets gardés (humidité, chauffage, soleil, fenêtres, équipements, personnes et alarme, prévisions, apprentissage) et le nombre de lignes.
3. **Mesures** : afficher ou non, les rubriques dans l’ordre voulu, dépliées ou non au départ.
4. **Détails techniques** : afficher ou non, les lignes gardées (plage, créneau, fenêtres, volets, personnes, séchage, tendance, capteurs), dépliés ou non.

Puis l’apparence (animations, verre dépoli) et l’appui long. Pour une tuile, un premier groupe règle ses pastilles et ce qui s’ouvre d’un appui (échelle, graphique, mesures, détails) ; chaque section garde les réglages ci-dessus.

**Le graphique « Prochaines heures »**, sous l’échelle : la pièce sans le geste conseillé (en pointillé gris) et avec (en couleur), une frise qui dit quand. Son sujet suit le conseil : rafraîchir la nuit en été, aérer sans perdre la chaleur en hiver, laisser le soleil réchauffer, assécher. Quand la température et l’humidité ont chacune quelque chose à montrer, deux onglets : celui du conseil d’abord. Il n’apparaît que quand il aide ; c’est une tendance, pas une mesure.

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

### Avec Adaptive Cover Pro

Si [Adaptive Cover Pro](https://github.com/jrhubott/adaptive-cover-pro) pilote un volet, Niak le reconnaît dès que vous choisissez ce volet dans **Ouvertures**. Le panneau affiche alors « Piloté par Adaptive Cover Pro » et la liste de ce qu’il lit.

Ce que Niak lit tout seul :

| Dans Adaptive Cover Pro | Ce qu’en fait Niak |
|---|---|
| Integration Enabled, Automatic Control, Sun Tracking | Les trois allumés : Adaptive Cover Pro pilote, Niak ne vous demande rien. Un seul coupé : Niak reprend ses conseils et dit lequel. |
| Manual Override Detection, Dérogation manuelle | Vous avez repris la main : Niak la respecte. Détection coupée : Niak ignore ce signal. |
| Climate Mode | Coupé dans une pièce trop chaude : Niak signale qu’il ne ferme pas contre la chaleur. |
| Soleil devant | Plus précis que la façade seule : sans soleil devant la fenêtre, rien à fermer. |
| Début et fin du soleil | Pièce déjà trop chaude : « à fermer avant 13 h 50 », si Adaptive Cover Pro ne pilote pas. |
| Position cible, raison | Visibles dans les détails de la carte. |
| Orientation, largeur, hauteur de la fenêtre | Reprises pour le calcul du soleil et de l’ombre. Une valeur saisie dans Niak reste prioritaire. |

Une fonction qu’Adaptive Cover Pro laisse indisponible (par exemple le mode climat non configuré) est simplement ignorée : ce n’est pas une panne.

Sur la carte de la pièce, la tuile **Volet** donne la position et une courte note : « automatique », « automatique · soleil devant », « automatisme coupé », « à fermer avant 13 h 50 » ou « à la main jusqu’à 15 h 00 ».

Seule l’avancée de toit reste à saisir : Adaptive Cover Pro ne la connaît pas.

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
- **Les murs** : le jumeau apprend aussi la masse de la pièce, qui suit l’air en quelques heures. Dix minutes d’aération refroidissent l’air, pas les murs ; une nuit entière, oui.
- **La nuit simulée** (avec Niak Weather, d’après la méthode de [NADIR](https://solal3105.github.io/NADIR2/methodologie.html), de Solal Gendrin ([son dépôt](https://github.com/solal3105/NADIR2))) : quand la pièce a chaud, Niak simule les 30 prochaines heures, fenêtres fermées puis ouvertes aux bons moments. Il pèse le soleil qui entrerait volets relevés contre l’air frais, n’ouvre ni sous la pluie ni sous votre minimum. « À savoir » dit alors : « Cette nuit : ouvrez de 22 h à 7 h · 1,8 °C de mieux demain au plus chaud », et signale un air humide. Fiable à l’heure près, pas à la décimale.

Dans **Détails**, la ligne **Séchage** dit sur combien d’aérations la pièce a appris.

### Apprentissage optimal

Niak rejoue chaque jour les prévisions de la pièce sur les dernières 24 heures. L’apprentissage est **optimal** après 7 jours de mesures, quand ces prévisions tiennent à ±0,5 °C et ±3 % d’humidité.

Alors le conseil est **optimisé** : il annonce le résultat, « Aérez 15 min · 76 → 68 % en 15 min », aussi pour le CO₂ et les COV. Une pastille « Conseil optimisé » le signale. Si les prévisions ne tiennent plus, la pièce repasse en conseil estimé.

Chaque aération conseillée et suivie est mesurée : la carte montre son résultat pendant 24 h, l’accueil Confort le bilan de la semaine.

Quand l’humidité d’une pièce monte souvent à la même heure, ou qu’une fenêtre reste ouverte la nuit, l’accueil pose une question : Oui, Non ou Je ne sais pas. Une cause n’est jamais devinée : seul un « Oui » la nomme.

L’accueil Confort montre où en est chaque pièce : optimal, en cours, à affiner ou à vérifier, avec la précision de ses prévisions et sa courbe sur 24 h.

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
