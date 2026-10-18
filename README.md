# Niak Comfort — intégration

[![release](https://img.shields.io/github/v/release/Niakman13/niak-comfort-integration?cacheSeconds=86400)](https://github.com/Niakman13/niak-comfort-integration/releases)
[![Validate](https://github.com/Niakman13/niak-comfort-integration/actions/workflows/validate.yml/badge.svg)](https://github.com/Niakman13/niak-comfort-integration/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange)](https://hacs.xyz)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Niakman13)
[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-frankblemont-FFDD00?logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/frankblemont)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?logo=paypal&logoColor=white)](https://paypal.me/frankblemont)

<img src="custom_components/niak_comfort/brand/icon.png" alt="" width="96" align="right">

**Le confort de chaque pièce, expliqué.** Niak Confort regarde vos pièces et le temps dehors. Il dit en une phrase quoi faire : ouvrir, fermer, attendre ou rien. Et il dit pourquoi.

Il conseille seulement : il ne commande aucun équipement.

![Niak Confort — la carte d’une pièce qui conseille d’aérer, à côté de la carte du logement](docs/images/niak-comfort-banner.png)

## Pourquoi

Un thermomètre donne un chiffre. Il ne dit pas s’il faut ouvrir la fenêtre.

Niak Confort compare dedans et dehors, et répond aux questions de tous les jours :

- **Il fait chaud** : faut-il ouvrir maintenant, ce soir, ou garder fermé ?
- **C’est humide** : aérer va-t-il vraiment assécher la pièce ? Combien de temps ?
- **L’air est lourd** : le CO₂ monte, c’est le moment d’aérer.
- **Il pleut, le vent souffle** : quelle fenêtre refermer ?

Chaque pièce apprend de ses aérations : les conseils s’ajustent à votre maison.

Toute la famille lit la même carte. Elle ne parle que quand un geste aide vraiment.

## Ce qu’il faut

- Home Assistant **2026.10** ou plus récent.
- Un thermomètre dans chaque pièce à suivre. C’est le seul capteur obligatoire.
- En plus, si vous en avez : humidité, CO₂, contacts de fenêtres, thermostat, VMC, purificateur, volets, présence.
- Pour l’extérieur : [Niak Weather](https://github.com/Niakman13/niak-weather-integration) (conseillé) ou vos propres capteurs.

## Installation

1. Dans HACS, ⋮ → **Dépôts personnalisés** : ajoutez `https://github.com/Niakman13/niak-comfort-integration`, catégorie **Intégration**.
2. Installez **Niak Comfort**, puis redémarrez Home Assistant.
3. **Paramètres → Appareils et services → Ajouter une intégration → Niak Comfort.**
4. Ouvrez **Niak** dans la barre latérale, onglet **Confort**.

[![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Niakman13&repository=niak-comfort-integration&category=integration)

La carte est fournie par l’intégration : rien d’autre à installer.

## Premiers pas

1. **Vos pièces** : Niak propose toutes les pièces où il trouve une température. Décochez celles à ne pas suivre, puis créez-les d’un coup.
2. **L’extérieur** : dans **Réglages généraux**, reprenez Niak Weather en un clic, ou choisissez vos capteurs. Il sert à toutes les pièces.
3. **Chaque pièce** : **Configurer** ouvre ses réglages. Niak propose les capteurs de la pièce : vous gardez, changez ou retirez.
4. **La carte** : sur un tableau de bord, **Ajouter une carte → Niak Confort**.

Rien n’est enregistré avant **Enregistrer**. [Le guide pas à pas](docs/guide.md).

## Les cartes

Deux cartes à choisir dans **Ajouter une carte** :

- **Niak Confort** : une pièce. Son conseil, sa température dans votre plage, ses mesures. Formats : complète, tuile, tuile dépliée, mini, mesures, alerte (visible seulement quand un geste est conseillé).
- **Niak Confort · logement** : toutes les pièces. Les conseils qui comptent, la température de chaque pièce, l’air qui traverse. Formats : complète, tuile, liste des pièces, mini, alerte.

Comme pour Niak Weather, un appui long sur une tuile (un appui sur mini et alerte) ouvre la carte complète en fenêtre, une page de votre choix, ou rien.

La couleur dit s’il y a quelque chose à faire :

- **bleu** : tout va bien ;
- **vert** : un bénéfice à saisir (« Aérez vers 23 h ») ;
- **orange** : un geste conseillé maintenant ;
- **rouge** : urgent (la pluie entre).

![Quatre pièces : tout va bien, aérer plus tard, lancer la VMC, fermer car il pleut](docs/images/niak-comfort-situations.png)

Un appui sur une mesure ouvre son historique dans Home Assistant. [Lire les conseils](docs/guide.md#lire-les-conseils).

## Le panneau Niak

Tout se règle dans le panneau **Niak** de la barre latérale, onglet **Confort**. Pas de YAML, pas de nom d’entité à connaître.

![Le panneau Niak, onglet Confort : les pièces du logement](docs/images/niak-comfort-panneau.png)

- **Vue d’ensemble** : vos pièces, avec **Configurer**, et ce qui reste à régler.
- **Réglages généraux** : l’extérieur, commun à toutes les pièces.
- Une pièce se règle en six onglets : Température, Ouvertures, Air intérieur, Présence, Chauffage, La pièce.

Chaque réglage a son aide. Les seuils sont expliqués avec leurs sources ([les repères](docs/SEUILS.md)).

## Avec Niak Weather et l’écosystème Niak

Niak Confort fonctionne seul. Avec [Niak Weather](https://github.com/Niakman13/niak-weather-integration), il devient plus malin :

- l’extérieur se règle en un clic : la station de votre lieu Weather ;
- il anticipe : « Refermez avant la pluie », « Ouvrez vers 22 h », rafraîchir la nuit avant une journée chaude ;
- il tient compte des vigilances et des orages ;
- l’air du dehors suit la source choisie dans Weather (Atmo France ou une station WAQI). Si Atmo France tombe en panne, Confort garde l’indice du jour. Il faut Niak Weather 2.5.7 ou plus récent.

Les deux briques partagent le panneau **Niak** et la même charte. L’**Accueil Niak** montre l’état de chacune.

## Pour vos automatisations

Chaque pièce crée quelques entités :

| Entité | Ce qu’elle dit |
| --- | --- |
| **Situation** | Tout va bien, potentiel, geste conseillé, attention, information incomplète |
| **Geste** | Ouvrir, fermer, attendre, aucun nouveau geste |
| **Raison** | Pourquoi : pluie, CO₂, rafraîchissement possible, soleil qui entre… |
| **Chauffage observé** | Chauffe, au repos, arrêté |
| **Couverture des données** | Toutes les sources répondent, ou bilan partiel |

Par exemple : une notification quand le geste du salon passe à **Fermer**. [Le détail des entités](docs/guide.md#pour-vos-automatisations).

## Documentation

| Page | Ce qu’elle explique |
| --- | --- |
| [Guide d’utilisation](docs/guide.md) | Premiers pas, extérieur, pièces, lire les conseils, équipements, apprentissage, entités |
| [Dépannage](docs/depannage.md) | « Ne répond pas », carte invisible, sources, Niak Weather, journaux |
| [Les repères](docs/SEUILS.md) | CO₂, particules, humidité, COV : les seuils proposés et leurs sources |
| [Notes techniques](docs/dev/README.md) | Pour les développeurs : tests, interfaces, notes de conception |

## Limites

Niak Confort conseille. Il n’ouvre, ne ferme et ne règle rien.

Une mesure absente reste inconnue : rien n’est inventé.

Les durées d’aération, l’ombre et la buée sont des estimations. Elles ne remplacent pas une mesure.

Un indice de qualité de l’air du jour ne mesure pas l’air devant vos fenêtres.

## Licence

[MIT](LICENSE) — Niakman13.
