## 0.9.0-beta.9 — Les conseils défilent, la carte se règle

- Quand il y a plusieurs conseils, ils défilent dans le bandeau, un toutes les 4,5 s, comme dans Niak Weather : le plus important d’abord, une barre par conseil, pause au survol, un appui pour passer au suivant. La carte garde la hauteur du conseil le plus long : plus de saut quand le texte change.
- Le purificateur qui tourne pendant que les particules sont élevées est un remède en cours : les particules seules ne demandent plus d’aérer, et la carte l’indique (« Le purificateur filtre »).
- Nouvelle source « Ventilation (VMC) » dans l’étape Air intérieur, distincte du purificateur : la carte indique qu’elle renouvelle l’air et aide à assécher.
- Réglages de la carte refaits, comme pour Weather : format (complète, tuile, mini), échelle, mesures et détails affichés ou non, dépliés ou repliés au départ, défilement automatique des conseils.

Si une VMC est déclarée comme purificateur dans une pièce, choisissez-la plutôt dans « Ventilation (VMC) ». Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.0-beta.8 — Une panne d’Atmo ne bloque plus le conseil

- Quand l’indice de qualité de l’air extérieur ne répond plus (panne d’Atmo France), le conseil reste valable au lieu de demander de « regarder dehors ». La panne est signalée dans « Détails » et dans l’état technique. La pluie reste une protection : si son capteur se tait, Niak demande toujours de vérifier.
- La carte distingue une source jamais configurée (« non suivie ») d’une source configurée qui ne répond pas (« indisponible »), et ne présente plus le chauffage comme une source extérieure.
- L’Accueil Niak signale aussi une source qui ne répond pas, même quand le conseil reste valable.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.0-beta.7 — Des cartes plus visuelles, une plage de confort qui suit les saisons

- Cartes pièce et logement refaites, moins de texte et plus visuelles : un bandeau avec le geste en quelques mots et sa raison en une ligne, un grand pictogramme, puis une échelle qui place la pièce dans votre plage (valeur actuelle, minimum et maximum des dernières 24 h, température dehors). Sur la carte logement, un point par pièce.
- Les mesures deviennent des tuiles compactes, repliables ; celles qui sortent de votre plage restent visibles et s’encadrent. Les explications passent derrière le bouton « i » et dans « Détails ».
- Même charte que Niak Weather : tailles de texte, étiquettes, couleurs, contours et sections repliables. La charte est désormais commune aux cartes Niak.
- La température maximale de confort suit la saison : 24 °C l’hiver, 26 °C l’été par défaut, avec un passage progressif quand la température extérieure moyenne des 7 derniers jours monte de 12 à 20 °C. Sans historique extérieur, la plage enregistrée reste inchangée.
- Nouveau réglage « Température maximum en été » ; les pièces existantes reçoivent 26 °C pour l’été, modifiable. Nouvelle option « Pièce non chauffée » : Niak ne conseille jamais de la réchauffer.
- Un contact qui s’ouvre moins d’une minute n’est plus compté comme une ouverture.

Bêta en observation. Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page du navigateur ou de l’application.

## 0.9.0-beta.6 — Formulaires harmonisés

- Les rubriques Weather reprennent les composants de Confort : réglages regroupés par sujet, mêmes titres et espacements, aides nommées en info-bulles.
- Les prévisions, alertes, mesures principales, sources d’air et de pollens et familles d’entités restent visibles. Les détails avancés gardent un repli.
- Les réglages généraux de Confort utilisent des lignes ouvertes à l’intérieur des groupes, sans cadre supplémentaire pour chaque capteur.

## 0.9.0-beta.5 — Affichage du hub

- L’accueil et le menu occupent toute la hauteur disponible dans Home Assistant, y compris lorsque seule une brique est à jour.
- Le menu de configuration d’une pièce s’aligne sur toute la largeur du formulaire.
- Dans Accueil Niak → Réglages, choix mémorisé entre les couleurs et la police du thème Home Assistant et la palette Niak. Niak conserve le suivi du mode clair ou sombre de Home Assistant.
- La section Affichage reste toujours visible, sans repli.

## 0.9.0-beta.4 — Le nouveau hub Niak

- Interface claire ou sombre, menu par brique et mise en page adaptée au téléphone.
- Vue d’ensemble des pièces avec Configurer. Les six rubriques restent dans la pièce choisie ; l’extérieur partagé est dans Réglages généraux.
- Menu des pièces en deux rangées de boutons avec icônes, sans glissière horizontale.
- Textes d’aide en info-bulles et valeurs par défaut explicites, avec possibilité de les rétablir ; recommandations et erreurs toujours visibles.
- Ouverture de Confort stabilisée : la liste des pièces apparaît sans attendre le bilan technique. Liens directs, retours arrière et brouillons séparés par pièce.
- Le menu ne propose que les briques installées ; l’entrée Niak du menu Home Assistant peut être masquée dans Réglages Niak.

Bêta en observation. Les paramètres existants sont conservés. Après mise à jour HACS, redémarrez Home Assistant.

## 0.9.0-beta.3 — Seuils expliqués auprès des capteurs

- Chaque capteur regroupe sa sélection, ses seuils modifiables et une explication repliable avec ses sources (HCSP, OMS, ADEME et fabricant).
- Repères proposés : CO₂ 800 / 1 000 / 1 500 ppm, PM2.5 15 µg/m³, humidité haute 60 %, indice COV 150 pour une IKEA VINDSTYRKA identifiée. La portée de chaque référence est explicitée, notamment moyenne OMS sur 24 h versus mesure ponctuelle et indice COV relatif versus concentration.
- Application unique de ces repères aux pièces existantes, puis conservation des personnalisations. Les seuils COV des modèles non reconnus ne sont pas remplacés par un indice arbitraire.
- « Pièce et confort » devient « Réglages / autres » pour les paramètres transversaux.

Après mise à jour HACS, redémarrez Home Assistant. Vérifiez les repères auprès des capteurs ; ils restent personnalisables.

## 0.9.0-beta.2 — Détection des indices COV IKEA

- Les indices VOC Zigbee2MQTT sans catégorie Home Assistant, notamment la sonde IKEA VINDSTYRKA, sont reconnus à partir de leur identifiant technique ; le nom de l’entité peut être personnalisé.
- Le rattachement à la pièce via l’appareil est conservé, ainsi que le seuil personnel dans l’indice sans unité, sans conversion en concentration.
- Les capteurs Atmo France mal catégorisés, dont les pollens, sont exclus des COV de pièce.

Après mise à jour HACS, redémarrez Home Assistant, puis recherchez à nouveau les capteurs dans la pièce.

## 0.9.0-beta.1 — Soleil, aération et présence

- Volets manuels en bois ou autres, volets reliés à Home Assistant, ou aucun volet : conseils par ouvrant, position inconnue conservée et dérogation suivie lorsqu’elle est renseignée.
- Soleil, luminosité et ombre estimée d’une avancée de toit ; dimensions facultatives.
- Durée d’aération indicative, temps d’ouverture lorsqu’il est connu, tendances de température et risque de buée estimé.
- PM2.5 et COV avec leurs unités et leurs seuils ; purificateur observé sans le confondre avec un renouvellement d’air.
- Présence facultative : une pièce vide reste suivie et les besoins mesurés restent visibles.

Bêta en observation. Niak conseille et ne commande aucun équipement. Après mise à jour HACS, redémarrez Home Assistant.

- La roue de l’intégration mène directement à l’onglet Confort.

## 0.6.0-beta.2 — Chargement fiable des cartes

- Les cartes du logement et des pièces attendent que Home Assistant soit prêt avant de s’enregistrer, y compris après un rechargement ou à la réouverture des onglets.
- La ressource du tableau de bord est tenue à jour automatiquement ; les anciennes adresses locales encodées sont regroupées.
- Le chargement de secours pour les tableaux de bord en YAML bénéficie de la même protection.

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
