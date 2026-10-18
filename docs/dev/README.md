# Notes techniques

Pour les développeurs. Le guide pour les utilisateurs est [ici](../guide.md).

## Tests et compilation

- Tests Python : Python 3.14, `pip install -r requirements-test.txt`, puis `python -m unittest discover -s tests -p 'test_*.py'`.
- Panneau : `cd frontend && npm ci && npm run validate` (produit `custom_components/niak_comfort/frontend/panel.js`).
- Carte : `cd card && npm ci && npm run validate` (produit `custom_components/niak_comfort/frontend/niak-comfort-card.js`).
- Chargement des cartes : `cd card && npx playwright install chromium firefox && NIAK_TEST_FIREFOX=1 npm run test:loading`. Vérifie les cartes logement et pièce, et leur éditeur, avant et après l’initialisation de Home Assistant, sur deux onglets, avec cache et rechargement.

## Bancs visuels

Données fictives, aucune connexion à un Home Assistant réel :

- `card/preview/refonte/` : la vraie carte compilée, nourrie par des situations calculées par le moteur Python (`scenes.py` → `scenes.json`) ;
- `card/preview/formats/` : les formats de carte ;
- `card/preview/card.html`, `floors.html`, `floor-settings.html` : carte, étages, réglage d’un étage ;
- `frontend/tests/hub-harness.mjs` : le panneau Niak (Accueil, Confort, Weather).

Les images de `docs/images/` viennent de ces bancs.

## Interfaces

- API WebSocket v1 en lecture : `niak_comfort/entries`, `niak_comfort/view`, `niak_comfort/subscribe`, `niak_comfort/home_subscribe`.
- Entités par pièce : situation, geste, raison, chauffage observé, couverture des données (identifiant interne `<entrée>_<clé>`).
- Niak Weather : `weather_link.py` lit son API publique (station, prévisions, `air()` depuis Weather 2.5.7).

## Notes de conception

| Note | Sujet |
| --- | --- |
| [CONFIGURATION-MON-LOGEMENT.md](CONFIGURATION-MON-LOGEMENT.md) | Le panneau « Mon logement » (0.3) |
| [ETAGES.md](ETAGES.md) | Logement et étages, données publiées (0.6) |
| [CHARGEMENT-CARTES.md](CHARGEMENT-CARTES.md) | Chargement fiable des cartes (0.6) |
| [BLOCS-7-8-9.md](BLOCS-7-8-9.md) | Soleil et volets, aération fine, air et présence : périmètre et limites (0.9) |
| [IMPLEMENTATION-7-8-9.md](IMPLEMENTATION-7-8-9.md) | Contrat de travail des blocs 7 à 9 |

Ces notes datent de leur version : elles ne décrivent pas toujours l’état actuel.
