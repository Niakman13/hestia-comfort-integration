# Niak Comfort — intégration

Moteur de confort par pièce pour Home Assistant. Il normalise les mesures, conserve les besoins simultanés et fournit une vue expliquée à [la carte Niak Comfort](https://github.com/Niakman13/niak-comfort).

**Version 0.2.0 — alpha de test, en observation.** Aucune commande d’équipement. Home Assistant 2026.10.0 minimum, version utilisée pour les contrôles isolés. L’installation complète dans une instance et les capteurs propres à chaque logement restent à vérifier.

## Installation

1. Dans HACS, ajouter `https://github.com/Niakman13/niak-comfort-integration` comme **dépôt personnalisé**, catégorie **Integration**. Télécharger l’alpha ; afficher les versions bêta si nécessaire. Ce projet n’est pas inclus au catalogue HACS par défaut.
2. Redémarrer Home Assistant.
3. Ajouter **Niak Comfort** dans Paramètres → Appareils et services.
4. Choisir une pièce HA, son nom, ses capteurs et ses repères. Une configuration par pièce.
5. Installer [la carte](https://github.com/Niakman13/niak-comfort#installation).

Installation manuelle : copier `custom_components/niak_comfort` de ce dépôt dans `config/custom_components/niak_comfort`, redémarrer puis ajouter l’intégration. Les templates existants ne sont ni importés ni remplacés.

## Mesures et réglages

Températures intérieure/extérieure requises ; humidités, CO₂, contacts d’ouvrants et chauffage facultatifs. Un champ laissé vide reste vide. Pluie et air extérieur défavorable utilisent des signaux binaires explicitement interprétés pour cette pièce. Sans ces vérifications, une possibilité d’ouverture reste à confirmer.

Températures °C/°F/K normalisées en °C, humidité en %, CO₂ en ppm. Valeurs absentes, non finies, incompatibles ou périmées exclues : aucun 600 ppm de remplacement. L’action chauffage utilise `hvac_action`, pas simplement le mode `heat`.

Repères thermiques, humidité et CO₂ configurables ; seuils initiaux historiques de démonstration, pas des références sanitaires. Hystérésis configurable. La fraîcheur s’appuie sur la dernière réception HA, pas une garantie sur l’heure physique de mesure. Sa durée maximum est encore commune aux sources de la pièce : l’adapter à leur cadence, notamment pour les contacts.

## États et interface

Cinq capteurs : situation, geste, raison stable, action chauffage observée et couverture. Les besoins simultanés et manques sont conservés. Vert OK, bleu potentiel, orange conseil, rouge attention, gris inconnu.

API WebSocket v1 en lecture : `niak_comfort/entries`, `niak_comfort/view`, `niak_comfort/subscribe`. Les changements de source et une vérification toutes les 30 secondes actualisent la vue. Le détail des observations reste hors des attributs volumineux de Recorder. Les abonnements annoncent les rechargements et peuvent être libérés sans commandes.

## Limites de l’alpha

Weather n’est pas raccordé ; pas de prévisions, vent, façades/volets, diagnostic PM2.5/COV ni coordination chauffage. Les protections extérieures sélectionnées doivent réellement correspondre aux fenêtres de la pièce. Aucun débit d’air, durée suffisante ou économie n’est garanti. La parité avec un ancien template personnalisé n’est pas annoncée.

Weather sera passif. Comfort publiera des besoins. Le futur chauffage décidera seul des commandes autorisées, en respectant modes manuels et protections natives. La vue actuelle de carte n’est pas encore une passerelle de commande.

## Tests

Moteur autonome : `python3 -m unittest discover -s tests -p test_engine.py` et `python3 -m unittest discover -s tests -p test_scenarios.py`.

Contrôles HA isolés : Python 3.14, `pip install -r requirements-test.txt`, puis `python -m unittest discover -s tests -p 'test_*.py'`. 38 tests, dont un replay de 12 situations. Aucun contact avec une instance réelle. Le test d’indisponibilité injecte volontairement une erreur dans les journaux.

`python3 scripts/export_card_fixtures.py` exporte des vues fictives du moteur pour le banc frontend dans `dist/card-fixtures.json`.

Licence MIT — Niakman13.
