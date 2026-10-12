# Niak Comfort — intégration

[![release](https://img.shields.io/github/v/release/Niakman13/niak-comfort-integration?include_prereleases&cacheSeconds=3600)](https://github.com/Niakman13/niak-comfort-integration/releases)
[![Validate](https://github.com/Niakman13/niak-comfort-integration/actions/workflows/validate.yml/badge.svg)](https://github.com/Niakman13/niak-comfort-integration/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange)](https://hacs.xyz)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Niakman13)
[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-frankblemont-FFDD00?logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/frankblemont)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?logo=paypal&logoColor=white)](https://paypal.me/frankblemont)

Moteur de confort par pièce pour Home Assistant. Il normalise les mesures, conserve les besoins simultanés et fournit une vue expliquée à [la carte Niak Comfort](https://github.com/Niakman13/niak-comfort).

**Version 0.3.0-beta.3 — bêta de test, en observation.** Aucune commande d’équipement. Home Assistant 2026.10.0 minimum, version utilisée pour les contrôles isolés. L’installation complète dans une instance et les capteurs propres à chaque logement restent à vérifier.

## Installation

1. Dans HACS, ouvrir le bouton ci-dessous (ou ⋮ → **Dépôts personnalisés** : `https://github.com/Niakman13/niak-comfort-integration`, catégorie **Intégration**). Télécharger l’alpha ; afficher les versions bêta si nécessaire. Ce projet n’est pas inclus au catalogue HACS par défaut.
2. Redémarrer Home Assistant.
3. Ajouter **Niak Comfort** dans Paramètres → Appareils et services.
4. Activer l’espace **Niak Confort**, puis l’ouvrir dans la barre latérale. Configurer le Salon ou une autre pièce ; vérifier les propositions et leur provenance avant d’enregistrer.
5. Installer [la carte](https://github.com/Niakman13/niak-comfort#installation).

[![Ouvrir Niak Comfort dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Niakman13&repository=niak-comfort-integration&category=integration)

Installation manuelle : copier `custom_components/niak_comfort` de ce dépôt dans `config/custom_components/niak_comfort`, redémarrer puis ajouter l’intégration. Les templates existants ne sont ni importés ni remplacés.

## Mon logement

La page **Niak Confort** est fournie par l’intégration, sans nécessiter la carte Lovelace. Elle est réservée aux administrateurs Home Assistant. Elle regroupe les pièces, les sources extérieures communes et un assistant unique pour ajouter ou modifier une pièce : intérieur, extérieur, fenêtres, chauffage, préférences et récapitulatif. Retour, accès direct aux catégories et configuration facultative ultérieure sont disponibles. Les changements restent en brouillon jusqu’à **Enregistrer** ; quitter la page demande d’abandonner le brouillon.

Les propositions utilisent les pièces HA, avec priorité à la pièce de l’entité puis à celle de l’appareil. Une référence température/humidité pertinente ou un candidat local unique peut être proposé. Plusieurs candidats ne donnent pas lieu à une sélection arbitraire. Les mesures reprises d’autres capteurs sont expliquées avec leur origine ; les contacts de type porte ne sont pas ajoutés automatiquement comme fenêtres. Les sources ambiguës nécessitent une confirmation explicite. Le choix d’un capteur d’une autre pièce reste possible, notamment pour une station mixte.

Les configurations existantes sont conservées. Ouvrir **Modifier** pour les revoir. Les pièces choisissent explicitement si elles utilisent les données extérieures communes ; les autres gardent leurs sources propres. Rechercher à nouveau les capteurs actualise les propositions sans réassigner un champ vide. La sauvegarde refuse un brouillon obsolète si la configuration a changé ailleurs.

## Mesures et réglages

La température intérieure est nécessaire ; humidité, CO₂, fenêtres et chauffage sont facultatifs. Les températures °C/°F/K sont normalisées en °C, humidité en %, CO₂ en ppm. Valeurs absentes, incompatibles ou périmées exclues, sans valeur de remplacement. L’action chauffage utilise `hvac_action`, pas simplement le mode `heat`.

Les données extérieures du logement acceptent températures/humidité, une intensité de pluie actuelle en mm/h ou in/h et l’indice global du jour de l’intégration Atmo France. Un cumul de pluie et une prévision ne deviennent pas une observation de pluie actuelle. Les anciens signaux binaires explicitement configurés restent disponibles ; les diagnostics de panne ne sont pas des sources de pluie ou pollution compatibles.

L’indice ATMO est un indicateur régional journalier, [publié comme prévision du jour et du lendemain](https://www.atmo-france.org/indiceatmo). Le panneau indique cette limite et laisse choisir le niveau à partir duquel appliquer une précaution. Un indice favorable ne certifie jamais que l’air à vos fenêtres permet une ouverture. Les sous-indices de polluants, le pollen et le lendemain ne sont pas assimilés à cet indice global. Le moteur expire un indice dont la mise à jour ne correspond plus à la journée locale.

L’exposition des ouvrants à la pluie est déclarée séparément pour chaque pièce. Déclarer les ouvrants à l’abri de la pluie ne renseigne pas le vent ni les projections.

La configuration initiale expose la plage de confort ; les réglages avancés restent facultatifs. Les seuils initiaux sont des repères de démonstration, pas des références sanitaires. La fraîcheur suit la dernière réception HA et conserve actuellement une durée commune aux mesures de la pièce.

## États et interface

Cinq capteurs : situation, geste, raison stable, action chauffage observée et couverture. Les besoins simultanés et manques sont conservés. Vert OK, bleu potentiel, orange conseil, rouge attention, gris inconnu.

API WebSocket v1 en lecture : `niak_comfort/entries`, `niak_comfort/view`, `niak_comfort/subscribe`. Les changements de source et une vérification toutes les 30 secondes actualisent la vue. Le détail des observations reste hors des attributs volumineux de Recorder. Les abonnements annoncent les rechargements et peuvent être libérés sans commandes.

## Limites de l’alpha

Les prévisions Niak Weather ne sont pas raccordées ; pas de prévisions, vent, façades/volets, diagnostic PM2.5/COV ni coordination chauffage. Les protections extérieures sélectionnées doivent réellement correspondre aux fenêtres de la pièce. Aucun débit d’air, durée suffisante ou économie n’est garanti. La parité avec un ancien template personnalisé n’est pas annoncée.

Weather sera passif. Comfort publiera des besoins. Le futur chauffage décidera seul des commandes autorisées, en respectant modes manuels et protections natives. La vue actuelle de carte n’est pas encore une passerelle de commande.

## Tests

Moteur autonome : `python3 -m unittest discover -s tests -p test_engine.py` et `python3 -m unittest discover -s tests -p test_scenarios.py`.

Contrôles HA isolés : Python 3.14, `pip install -r requirements-test.txt`, puis `python -m unittest discover -s tests -p 'test_*.py'`. 62 tests, dont un replay de 12 situations, les cas de détection/configuration et les vérifications de provenance, permissions et sauvegarde de l’espace Mon logement. Aucun contact avec une instance réelle. Le test d’indisponibilité injecte volontairement une erreur dans les journaux.

`python3 scripts/export_card_fixtures.py` exporte des vues fictives du moteur pour le banc frontend dans `dist/card-fixtures.json`.

Licence MIT — Niakman13.

Panneau : `cd frontend && npm ci && npm run validate`. La compilation produit le module fourni dans `custom_components/niak_comfort/frontend/panel.js`. Les tests du modèle, le contrôle TypeScript et la compilation sont aussi exécutés en CI.
