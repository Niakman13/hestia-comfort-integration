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
