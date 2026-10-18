# Dépannage

Commencez par l’**Accueil Niak** : il dit ce qui va, et ce qui reste à régler en orange.

Puis ouvrez **Confort → Vue d’ensemble**. La section **À régler** liste chaque problème, avec un bouton vers le bon réglage.

- [Un capteur ne répond pas](#un-capteur-ne-répond-pas)
- [Mesures en chargement ou absentes](#mesures-en-chargement-ou-absentes)
- [Calcul arrêté dans une pièce](#calcul-arrêté-dans-une-pièce)
- [La carte est invisible](#la-carte-est-invisible)
- [L’extérieur et Niak Weather](#lextérieur-et-niak-weather)
- [La qualité de l’air](#la-qualité-de-lair)
- [Un conseil semble faux](#un-conseil-semble-faux)
- [Les journaux](#les-journaux)
- [Signaler un problème](#signaler-un-problème)

## Un capteur ne répond pas

Exemple : « Cuisine : le CO₂ ne répond pas · Depuis 2 h ».

Home Assistant dit que ce capteur est indisponible ou inconnu.

1. Ouvrez le capteur dans Home Assistant : sa pile, sa connexion, son intégration.
2. S’il revient, Niak le reprend tout seul.
3. S’il est remplacé, choisissez le nouveau dans les réglages de la pièce.

« **N’existe plus** » : l’entité a été supprimée ou renommée. Choisissez-la à nouveau.

Ce qui manque reste inconnu : Niak conseille avec le reste. Seule la température de la pièce est indispensable.

Beaucoup de capteurs n’envoient une valeur que quand elle change. Une valeur stable reste valable tant que l’appareil donne signe de vie, et au plus 3 heures (réglable dans **La pièce → Réglages avancés**).

## Mesures en chargement ou absentes

**Mesures en chargement** : Home Assistant vient de démarrer. Les capteurs arrivent un à un. Attendez quelques minutes.

**Mesures absentes**, en gris : les capteurs de la pièce restent muets. Ce n’est pas un conseil. Voir [un capteur ne répond pas](#un-capteur-ne-répond-pas).

Un capteur secondaire muet (le CO₂, par exemple) ne change pas le conseil. Sa tuile passe en pointillés.

## Calcul arrêté dans une pièce

Home Assistant n’a pas pu démarrer cette pièce.

1. Vérifiez ses capteurs dans ses réglages.
2. **Paramètres → Appareils et services → Niak Comfort** : rechargez la pièce.
3. Si rien ne change, regardez [les journaux](#les-journaux).

## La carte est invisible

La carte est fournie par l’intégration : rien à installer à part.

- **Juste après une mise à jour** : redémarrez Home Assistant, puis rechargez la page.
- **Dans l’application Home Assistant** : **Paramètres → Application compagnon → Dépannage → Réinitialiser le cache du frontend**.
- **Vous aviez installé l’ancienne carte** (dépôt `niak-comfort`) : supprimez-la de HACS, puis rechargez la page. Vos cartes restent en place.
- **« Ouvrez Niak Confort dans la barre latérale »** : aucune pièce n’est encore créée.
- **« Connexion indisponible »** : la carte réessaie seule. Vérifiez que Home Assistant répond.

## L’extérieur et Niak Weather

**« Extérieur à configurer »** : sans l’extérieur, Niak ne peut pas dire s’il vaut mieux ouvrir ou fermer. Réglez-le dans **Confort → Réglages généraux**.

**Niak Weather est installé, mais n’est pas proposé** :

- vérifiez que Niak Weather a au moins un lieu (onglet **Météo** du panneau Niak) ;
- Confort a besoin de Niak Weather 2.1 ou plus récent ;
- après l’installation de Weather, redémarrez Home Assistant.

Une fois relié, la **Vue d’ensemble** de Confort indique « Relié à Niak Weather ». Weather affiche aussi « Relié à Niak Confort ».

**Pas d’anticipation** (« Refermez avant la pluie », « Aérez vers 22 h ») : elle vient des prévisions de Niak Weather.

## La qualité de l’air

**« Pollution · ne répond pas »** : la source de l’indice ne donne plus de valeur.

Le conseil reste valable. Niak le signale dans **Détails** et sur l’Accueil Niak.

Seule la pluie reste une protection : si son capteur se tait, Niak demande de vérifier dehors.

**Atmo France est en panne** : avec Niak Weather 2.5.7 ou plus, choisissez une station WAQI dans **Weather → Qualité de l’air**. Confort suit ce choix, sans autre réglage.

**Votre propre capteur de pollution** est gardé tel quel : il ne suit pas Niak Weather.

## Un conseil semble faux

Ouvrez **Détails** sur la carte. Vous y voyez :

- les mesures utilisées, leur source et leur âge ;
- ce qui manque ;
- l’apprentissage de la pièce (« Séchage »).

Vérifiez aussi les réglages de la pièce :

- **l’exposition** des fenêtres : elle décide du soleil et de la pluie ;
- **abrité** : une fenêtre abritée peut rester ouverte sous la pluie ;
- **votre plage** de température et le seuil d’humidité ;
- **Pièce non chauffée**, si la pièce n’a pas de chauffage.

« **Rien à faire** » alors qu’il fait chaud ? Dehors n’est pas plus frais, ou ouvrir n’aiderait pas. Niak ne parle que pour un geste utile.

La durée d’aération change ? La pièce apprend. Les premiers jours, elle reste prudente.

## Les journaux

**Paramètres → Système → Journaux**, puis cherchez « niak ».

Pour plus de détails, ajoutez dans `configuration.yaml`, puis redémarrez :

```yaml
logger:
  default: warning
  logs:
    custom_components.niak_comfort: debug
```

Retirez-le une fois le problème trouvé : les journaux grossissent vite.

Deux messages connus, sans gravité :

- « Home Assistant statistics could not be read » : la plage d’été ou le minimum de 24 h attendent l’historique ;
- « Past openings could not be read for … » : la pièce garde ce qu’elle avait appris.

## Signaler un problème

Ouvrez un ticket sur [GitHub](https://github.com/Niakman13/niak-comfort-integration/issues), avec :

- les versions de Home Assistant, Niak Confort et Niak Weather ;
- la pièce concernée et ce que dit la carte ;
- une capture de **Détails** ;
- les lignes des journaux qui contiennent « niak ».

Retirez vos informations personnelles avant d’envoyer.
