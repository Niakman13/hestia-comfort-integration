# Chargement des cartes — 0.6.0-beta.2

## Défaut confirmé le 16 octobre 2026

Dans l’onglet Home Assistant en erreur, `home-assistant` et `hestia-weather-card` étaient enregistrés, tandis que `hestia-comfort-card` et `hestia-comfort-home-card` manquaient. Le fichier Confort avait pourtant été chargé et ses entrées figuraient encore dans `window.customCards`.

Le serveur servait Confort 0.6.0-beta.1 sans protection au début du bundle. Weather 2.4.0 comportait déjà celle du socle 1.4. La correction préparée pour Confort n’avait pas été publiée avec la beta.1.

Home Assistant installe son registre de composants pendant son initialisation. Une carte exécutée avant ce remplacement peut s’enregistrer dans l’ancien registre et disparaître du registre utilisé par le tableau de bord. Un fichier en cache ou plusieurs onglets rendent l’ordre de chargement variable ; vider le cache ne corrige pas cette course.

## Correction

- Tout le bundle, Lit et décorateurs compris, attend `home-assistant`. Une attente placée après les imports TypeScript serait trop tardive.
- Après chaque attente, le registre courant est relu : la promesse pouvait appartenir au registre précédent.
- Le socle 1.4 donne la priorité à la ressource de tableau de bord, avec une adresse versionnée. Le module supplémentaire est réservé au repli YAML ou à un échec d’enregistrement.
- Les anciennes variantes locales encodées sont migrées et les doubles enregistrements sont protégés.
- Le changement de version de l’intégration change aussi l’adresse de la ressource, afin de charger le nouveau fichier.

## Validation locale

- L’ancien bundle de la beta.1 échoue au test de chargement précoce : Lit s’exécute avant Home Assistant.
- Le nouveau bundle passe sur Chromium et Firefox, à 1280 et 390 pixels, avec le polyfill de registre utilisé par Home Assistant (`@webcomponents/scoped-custom-element-registry` 0.0.10).
- Les essais couvrent le chargement avant le remplacement du registre, deux onglets partageant le cache HTTP, le rechargement avec cache, le chargement depuis le tableau de bord et une ressource déclarée plusieurs fois, y compris avec une adresse encodée.
- Les deux cartes et leur éditeur restent enregistrés. Les cartes rendent leur contenu et apparaissent une seule fois dans le sélecteur de cartes. Aucune erreur JavaScript dans ces scénarios.
- 143 tests Python réussis, dont 6 tests avec les vraies collections de ressources de Home Assistant : stockage, YAML, repli sur erreur, migration, type de ressource et suppression.
- 15 tests de carte et 10 tests de réglages réussis ; vérifications TypeScript et compilations réussies.

Ces essais simulent la reprise de plusieurs onglets avec un cache partagé. Ils ne constituent pas un essai de restauration du navigateur après redémarrage de l’ordinateur ni un essai dans l’application Companion réelle. La mise à jour de l’installation réelle reste à valider après publication et installation de la beta.2.
