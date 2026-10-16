# Niak Comfort — intégration

[![release](https://img.shields.io/github/v/release/Niakman13/niak-comfort-integration?include_prereleases&cacheSeconds=3600)](https://github.com/Niakman13/niak-comfort-integration/releases)
[![Validate](https://github.com/Niakman13/niak-comfort-integration/actions/workflows/validate.yml/badge.svg)](https://github.com/Niakman13/niak-comfort-integration/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange)](https://hacs.xyz)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Niakman13)
[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-frankblemont-FFDD00?logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/frankblemont)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?logo=paypal&logoColor=white)](https://paypal.me/frankblemont)

Le confort de chaque pièce, expliqué : ouvrir, fermer, attendre ou ne rien faire, et pourquoi. Une seule intégration contient le moteur, la page de configuration **Niak Confort** et la carte.

**Version 0.9.0-beta.3 — bêta de test, en observation.** Niak conseille, il ne commande aucun équipement. Home Assistant 2026.10.0 minimum.

**Logement et étages** : regroupement des pièces par étage Home Assistant, moyennes et conseils d’aération, avec prise en charge du plain-pied. Voir [le fonctionnement et les vérifications](docs/ETAGES.md).

## Soleil, aération et air

Les volets peuvent être manuels (bois, battants ou autres), reliés à Home Assistant, ou absents. Niak donne des conseils sans commander les équipements et sans inventer la position d’un volet manuel. Les dimensions facultatives affinent les estimations d’ombre et d’aération.

La carte suit le temps d’ouverture connu, les tendances de température et le risque de buée estimé. Les durées d’aération restent indicatives. PM2.5, COV, présence et purificateur sont facultatifs : les polluants restent distingués, et une pièce vide conserve son suivi. Les COV nécessitent un seuil choisi dans l’unité du capteur.

Voir [le périmètre et les limites des blocs 7 à 9](docs/BLOCS-7-8-9.md).

## Installation

1. Dans HACS, ouvrir le bouton ci-dessous (ou ⋮ → **Dépôts personnalisés** : `https://github.com/Niakman13/niak-comfort-integration`, catégorie **Intégration**), puis télécharger. Afficher les versions bêta si nécessaire.
2. Redémarrer Home Assistant.
3. Ajouter **Niak Comfort** dans Paramètres → Appareils et services.
4. Ouvrir **Niak** dans la barre latérale, onglet **Confort** : Niak propose toutes les pièces où il trouve une température. Décochez celles à ne pas suivre et créez-les d’un coup.
5. Dans un tableau de bord, ajoutez la carte **Niak Confort** (une pièce) ou **Niak Confort · logement** (toutes les pièces).

[![Ouvrir Niak Comfort dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Niakman13&repository=niak-comfort-integration&category=integration)

La carte est incluse : rien à déclarer. Niak Confort l’ajoute lui-même aux ressources des tableaux de bord et la tient à jour, pour que l’application mobile la trouve aussi. L’ancien dépôt séparé de la carte (`niak-comfort`) est archivé ; si vous l’aviez installé, supprimez-le de HACS.

## Mon logement

- **Pièces** : rattachées à une pièce Home Assistant (Niak propose ses capteurs) ou libres (« Étage », « Suite parentale »). Les pièces extérieures (Extérieur, Jardin, Terrasse…) ne sont pas proposées comme pièces.
- **Capteurs** : les propositions de la pièce, ou n’importe quel capteur avec le sélecteur de Home Assistant (recherche, « Pièce ▸ Appareil »). Une station mixte rattachée à l’extérieur peut servir de mesure intérieure.
- **Ouvrants** : pour chaque fenêtre ou porte, son exposition (N, NE, E…), son type (fenêtre, porte-fenêtre, vasistas, porte) et s’il est abrité par une avancée de toit.
- **Extérieur** : température, humidité, pluie actuelle (mm/h), rafales, ensoleillement (W/m²) et indice ATMO. Choisi une fois, utilisé par toutes les pièces.
- Les capteurs à vérifier demandent une confirmation, mémorisée ensuite. Rien n’est enregistré avant **Enregistrer**.

## Ce que Niak conseille

Trop chaud, trop froid, air à renouveler (CO₂), air trop humide : Niak compare dedans et dehors et dit si ouvrir aide. Il conseille de fermer les ouvrants exposés à la pluie (pas ceux qui sont abrités), de ne rien laisser ouvert au-delà de 45 km/h de rafales, de limiter l’aération quand il gèle ou que le chauffage tourne (une aération courte reste conseillée si le CO₂ est élevé), et signale la fenêtre ouverte par laquelle le soleil chauffe la pièce. Avec l’exposition des ouvrants et la direction du vent, il dit **quelles fenêtres ouvrir** (au vent et sous le vent) pour faire traverser l’air, et repère la pluie poussée sous un avant-toit. Tous les seuils se règlent dans les réglages avancés de chaque pièce.

## Avec Niak Weather

Si [Niak Weather](https://github.com/Niakman13/niak-weather-integration) (2.1.0b1 ou plus récent) est installé, la page de l’extérieur propose de reprendre sa station en un clic. Niak Confort lit alors aussi ses alertes et ses prévisions : orage, vigilance orange ou rouge, pluie qui arrive (« refermez avant la pluie »), créneau d’ouverture (« ouvrez vers 21 h, vent d’ouest ») et pré-rafraîchissement la nuit avant une journée chaude.

Une mesure absente reste inconnue : aucune valeur de remplacement. Si la pluie ou la qualité de l’air ne sont pas suivies, Niak conseille quand même et le précise sur la carte.

## Les cartes

- **Niak Confort** : une pièce, avec son conseil, ses mesures en bulles et ses ouvrants.
- **Niak Confort · logement** : la synthèse de toutes les pièces (celle qui demande le plus d’attention, la plus chaude et la plus fraîche, ce qui est ouvert, l’air qui traverse, par où commencer pour rafraîchir).

## À venir

Volets et luminosité, taille des ouvrants et aération traversante, durée d’aération, buée, présence, particules et COV, prévisions. Le détail est dans le cahier des charges du projet.

## Pour les développeurs

- Tests Python : Python 3.14, `pip install -r requirements-test.txt`, puis `python -m unittest discover -s tests -p 'test_*.py'`.
- Panneau : `cd frontend && npm ci && npm run validate` (produit `custom_components/niak_comfort/frontend/panel.js`).
- Carte : `cd card && npm ci && npm run validate` (produit `custom_components/niak_comfort/frontend/niak-comfort-card.js`). Banc de la carte avec des données fictives : `card/preview/card.html`.
- Chargement des cartes : `cd card && npx playwright install chromium firefox && NIAK_TEST_FIREFOX=1 npm run test:loading`. Vérifie les cartes logement et pièce, ainsi que leur éditeur, avant et après l’initialisation de Home Assistant, sur deux onglets, avec cache et rechargement. [Diagnostic et validation](docs/CHARGEMENT-CARTES.md).
- API WebSocket v1 en lecture : `niak_comfort/entries`, `niak_comfort/view`, `niak_comfort/subscribe`.

Licence MIT — Niakman13.
