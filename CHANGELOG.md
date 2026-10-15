## 0.6.0-beta.1 — Logement et étages

- La carte logement regroupe les pièces par étage Home Assistant, avec moyenne, nombre de mesures disponibles et pièce la plus chaude.
- Une pièce libre peut choisir un étage existant ; les pièces rattachées reprennent automatiquement celui de Home Assistant.
- Les logements de plain-pied gardent une synthèse complète et les possibilités d’aération traversante, sans réglage d’étage obligatoire.
- Les conseils proposent, lorsque les conditions le permettent, deux ouvertures pour l’effet cheminée ou une aération traversante. Ils expliquent les conditions et les limites du passage de l’air.
- Une pièce devenue indisponible reste visible ; sa température est exclue des moyennes. Les changements d’étage se répercutent sur la carte.

Bêta en observation, vérifiée localement. Niak conseille, sans commander les équipements.

## 0.5.0-beta.9 — Des étapes plus claires dans l’onglet Confort

- Les étapes d’une pièce disent ce qu’on règle : Température et humidité, Fenêtres et portes, CO₂, Chauffage, Pièce et confort.
- En haut de chaque étape, un cadre « À quoi sert cet onglet ? » ; replié, il le reste.
- À l’extérieur, les mesures sont rangées en cadres : Température et humidité, Pluie et vent, Soleil.
- Les mesures du dehors viennent de Niak Weather ou de vos capteurs ; la qualité de l’air, d’Atmo France ou de Niak Weather, puis sa zone.
- Une intégration absente est grisée, avec un lien pour l’installer.

## 0.5.0-beta.8 — Le lien avec Niak Weather des deux côtés

- Niak Weather affiche lui aussi « Relié à Niak Confort ».
- Le lien avec Niak Weather tient dès le démarrage de Home Assistant.

## 0.5.0-beta.7 — La carte visible dans l’application mobile

- La carte Niak Confort s’affiche aussi dans l’application Home Assistant, même juste après une mise à jour.
- Elle apparaît désormais dans Paramètres → Tableaux de bord → Ressources : c’est Niak Confort qui la tient à jour, rien à faire.
- Carte toujours invisible dans l’application ? Paramètres → Application compagnon → Dépannage → Réinitialiser le cache du frontend, une seule fois.

## 0.5.0-beta.6 — L’état technique du logement

- L’onglet Confort du panneau Niak s’ouvre sur l’état du logement, en cadres : ce qui fonctionne, ce qui est à régler, ce qu’on peut améliorer.
- À régler : un capteur d’une pièce ou de l’extérieur qui ne répond pas, avec ce que ça interrompt.
- À améliorer : un capteur disponible dans une pièce, des fenêtres non mesurées, une pièce pas encore suivie.
- Un tableau montre les capteurs de chaque pièce. Le bouton Modifier mène aux pièces ; chaque ligne ouvre la bonne pièce.

## 0.5.0-beta.5 — Le panneau Niak

- Les réglages sont dans **Niak** (barre latérale), onglet **Confort**.
- Un onglet **Accueil** montre l’état de Niak Confort : en bleu si tout est suivi, en orange s’il y a quelque chose à régler.
- Les autres briques Niak installées (Niak Weather) y apparaissent aussi.
- L’ancienne adresse et le bouton « Configurer » mènent toujours aux réglages.

## 0.5.0-beta.4 — Fenêtres ouvertes depuis longtemps

- Une fenêtre ouverte (ou fermée) depuis plus de 30 minutes n’est plus considérée comme « à vérifier » : un contact ne parle que quand il change.
- Même chose pour l’état du chauffage.
- L’indice ATMO sous votre seuil ne rend plus le bilan incomplet : Niak conseille normalement, et bloque toujours au-dessus du seuil.
- La carte nomme la fenêtre en cause (« Fenêtre Ouest ») au lieu de « Contact de fenêtre ».

## 0.5.0-beta.3 — Indice ATMO du matin

- L’indice ATMO du jour, publié la veille, est de nouveau pris en compte le matin : fini « Information incomplète » entre minuit et la mise à jour d’ATMO.
- Quand une mesure n’est pas à jour, la carte dit laquelle (« Qualité de l’air dehors : ne répond pas ou est trop ancienne »).

## 0.5.0-beta.2 — Supprimer une pièce

- Une pièce peut être supprimée depuis son assistant (« Supprimer cette pièce », avec confirmation).
- Vos capteurs et appareils Home Assistant ne sont pas touchés.
- La pièce Home Assistant supprimée est de nouveau proposée dans Mon logement.

## 0.5.0-beta.1 — Niak Weather et le vent

- Niak Weather est détecté : un clic reprend sa station pour l’extérieur (avec Niak Weather 2.1.0b1 ou plus récent).
- Le vent compte : Niak dit quelles fenêtres ouvrir, au vent et sous le vent, pour faire traverser l’air.
- La pluie poussée par le vent est repérée, même sous un avant-toit.
- Créneaux d’ouverture : « Ouvrez vers 21 h : il fera 18 °C, vent d’ouest ».
- Orage, vigilance orange ou rouge, pluie qui arrive : Niak conseille de fermer à temps.
- La nuit avant une journée chaude, Niak propose de stocker le frais.

## 0.4.0-beta.4 — Logement et carte plus visuelle

- Première installation : toutes les pièces détectées sont proposées, cochées, et créées d’un coup.
- Nouvelle carte « Niak Confort · logement » : la pièce qui demande le plus d’attention, la plus chaude, la plus fraîche, ce qui est ouvert.
- Carte d’une pièce plus visuelle et deux fois plus courte : des bulles de mesures, les ouvrants en pastilles, les explications derrière « Pourquoi ? ».
- Sans indice ATMO ni capteur de pluie, Niak conseille quand même et précise ce qu’il ne surveille pas.

## 0.4.0-beta.3 — Récapitulatif allégé

- Récapitulatif court : une ligne par catégorie.
- Une seule case à cocher pour confirmer les capteurs à vérifier, au lieu d’une par capteur.
- Une ancienne pièce n’est plus bloquée par des capteurs extérieurs invisibles dans la page.

## 0.4.0-beta.2 — Changer un capteur en un clic

- Chaque capteur choisi peut être remplacé directement, sans le retirer d’abord ; un ouvrant garde son exposition.
- Les anciennes pièces utilisent elles aussi l’extérieur commun dès qu’il est configuré.
- La carte s’appelle « Niak Confort » dans la liste des cartes.
- Un capteur qui ne répond pas est indiqué plus clairement.

## 0.4.0-beta.1 — Pièces, ouvrants et extérieur

- La carte est incluse dans l’intégration : un seul téléchargement, rien à déclarer.
- Salon proposé au départ ; pièces libres, sans pièce Home Assistant.
- Choix des capteurs avec le sélecteur de Home Assistant.
- Exposition, type et abri de chaque fenêtre ou porte.
- L’extérieur s’applique à toutes les pièces ; rafales et ensoleillement ajoutés.
- Pluie : seuls les ouvrants exposés sont à fermer.
- Nouveaux conseils : rafales fortes, gel, chauffage en marche, soleil qui entre par une fenêtre ouverte.
- Les capteurs confirmés ne sont plus redemandés.

## 0.3.0-beta.3 — Mon logement

- Configuration dans une page Niak Confort de la barre latérale, avec Salon proposé et ajout des pièces Home Assistant.
- Parcours par catégories, propositions expliquées, correction manuelle et récapitulatif avant enregistrement.
- Données extérieures communes sur activation explicite par pièce ; pluie actuelle et indice ATMO quotidien expliqués.
- Les alias de capteurs, portes d’appareils et diagnostics ne sont plus sélectionnés automatiquement. Les choix existants et champs volontairement vides sont conservés.

# Historique

## 0.3.0-beta.2 — deuxième préversion de test

- Assistant par catégories, détection par pièce et choix manuels.
- Récapitulatif avant enregistrement et modification par catégorie.
- Recherche explicite conservant les choix existants.
- Température extérieure facultative et chauffage non configuré explicite.

## 0.2.0 — alpha

Première publication de test. Observation et conseils par pièce, sans commande d’équipement. Weather, prévisions et coordination chauffage restent à raccorder.
