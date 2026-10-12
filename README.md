# Niak Comfort — intégration

[![release](https://img.shields.io/github/v/release/Niakman13/niak-comfort-integration?include_prereleases&cacheSeconds=3600)](https://github.com/Niakman13/niak-comfort-integration/releases)
[![Validate](https://github.com/Niakman13/niak-comfort-integration/actions/workflows/validate.yml/badge.svg)](https://github.com/Niakman13/niak-comfort-integration/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange)](https://hacs.xyz)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Niakman13)
[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-frankblemont-FFDD00?logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/frankblemont)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?logo=paypal&logoColor=white)](https://paypal.me/frankblemont)

Moteur de confort par pièce pour Home Assistant. Il normalise les mesures, conserve les besoins simultanés et fournit une vue expliquée à [la carte Niak Comfort](https://github.com/Niakman13/niak-comfort).

**Version 0.3.0-beta.2 — bêta de test, en observation.** Aucune commande d’équipement. Home Assistant 2026.10.0 minimum, version utilisée pour les contrôles isolés. L’installation complète dans une instance et les capteurs propres à chaque logement restent à vérifier.

## Installation

1. Dans HACS, ouvrir le bouton ci-dessous (ou ⋮ → **Dépôts personnalisés** : `https://github.com/Niakman13/niak-comfort-integration`, catégorie **Intégration**). Télécharger l’alpha ; afficher les versions bêta si nécessaire. Ce projet n’est pas inclus au catalogue HACS par défaut.
2. Redémarrer Home Assistant.
3. Ajouter **Niak Comfort** dans Paramètres → Appareils et services.
4. Suivre l’assistant : pièce (Salon proposé), intérieur, extérieur, fenêtres, chauffage et préférences. Vérifier le récapitulatif avant de confirmer. Une configuration par pièce ; ajouter les suivantes avec **Ajouter un service**.
5. Installer [la carte](https://github.com/Niakman13/niak-comfort#installation).

[![Ouvrir Niak Comfort dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Niakman13&repository=niak-comfort-integration&category=integration)

Installation manuelle : copier `custom_components/niak_comfort` de ce dépôt dans `config/custom_components/niak_comfort`, redémarrer puis ajouter l’intégration. Les templates existants ne sont ni importés ni remplacés.

## Mesures et réglages

Température intérieure requise ; température extérieure, humidités, CO₂, contacts d’ouvrants et chauffage facultatifs. Sans température extérieure, un bénéfice thermique d’ouverture n’est pas confirmé. Les capteurs sont proposés à partir des pièces HA (affectation de l’entité, puis de son appareil), avec priorité aux références température/humidité de la pièce. Plusieurs candidats nécessitent un choix ; les capteurs de toute l’installation restent accessibles pour les stations mixtes. Les contacts détectés doivent être vérifiés, notamment les doublons et états agrégés de thermostats. Un champ laissé vide reste vide. Pluie et air extérieur défavorable utilisent des signaux binaires explicitement interprétés pour cette pièce. Sans ces vérifications, une possibilité d’ouverture reste à confirmer.

Températures °C/°F/K normalisées en °C, humidité en %, CO₂ en ppm. Valeurs absentes, non finies, incompatibles ou périmées exclues : aucun 600 ppm de remplacement. L’action chauffage utilise `hvac_action`, pas simplement le mode `heat`.

La configuration initiale présente seulement la plage de confort. Le menu **Configurer** permet ensuite de modifier une catégorie, d’accéder aux réglages avancés et de rechercher explicitement de nouveaux capteurs sans remplacer les choix confirmés. Température/humidité extérieures et signal d’air défavorable déjà communs aux pièces sont proposés à l’ajout suivant, puis copiés dans la configuration de la nouvelle pièce : modifier une pièce ne modifie pas les autres. La pluie n’est pas héritée, car l’exposition dépend des fenêtres.

Repères thermiques, humidité et CO₂ configurables ; seuils initiaux historiques de démonstration, pas des références sanitaires. Hystérésis configurable. La fraîcheur s’appuie sur la dernière réception HA, pas une garantie sur l’heure physique de mesure. Sa durée maximum est encore commune aux sources de la pièce : l’adapter à leur cadence, notamment pour les contacts.

## États et interface

Cinq capteurs : situation, geste, raison stable, action chauffage observée et couverture. Les besoins simultanés et manques sont conservés. Vert OK, bleu potentiel, orange conseil, rouge attention, gris inconnu.

API WebSocket v1 en lecture : `niak_comfort/entries`, `niak_comfort/view`, `niak_comfort/subscribe`. Les changements de source et une vérification toutes les 30 secondes actualisent la vue. Le détail des observations reste hors des attributs volumineux de Recorder. Les abonnements annoncent les rechargements et peuvent être libérés sans commandes.

## Limites de l’alpha

Weather n’est pas raccordé ; pas de prévisions, vent, façades/volets, diagnostic PM2.5/COV ni coordination chauffage. Les protections extérieures sélectionnées doivent réellement correspondre aux fenêtres de la pièce. Aucun débit d’air, durée suffisante ou économie n’est garanti. La parité avec un ancien template personnalisé n’est pas annoncée.

Weather sera passif. Comfort publiera des besoins. Le futur chauffage décidera seul des commandes autorisées, en respectant modes manuels et protections natives. La vue actuelle de carte n’est pas encore une passerelle de commande.

## Tests

Moteur autonome : `python3 -m unittest discover -s tests -p test_engine.py` et `python3 -m unittest discover -s tests -p test_scenarios.py`.

Contrôles HA isolés : Python 3.14, `pip install -r requirements-test.txt`, puis `python -m unittest discover -s tests -p 'test_*.py'`. 49 tests, dont un replay de 12 situations et les cas de détection/configuration par pièce. Aucun contact avec une instance réelle. Le test d’indisponibilité injecte volontairement une erreur dans les journaux.

`python3 scripts/export_card_fixtures.py` exporte des vues fictives du moteur pour le banc frontend dans `dist/card-fixtures.json`.

Licence MIT — Niakman13.
