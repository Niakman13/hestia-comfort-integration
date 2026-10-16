# Contrat de travail des blocs 7–9

Plan validé par la maquette puis « go publie » le 16 octobre 2026. Implémenter, vérifier, publier 0.9.0-beta.1 ; pas de changement de production HA. Trois lots parallèles, puis revue et tests communs.

## Configuration

Sources additionnelles de pièce dans `sources` (toujours string par clé) : `illuminance`, `pm25`, `voc`, `purifier`. `presence` est une liste de binary_sensor au niveau racine, comme `windows`. Découverte explicite `presence` (occupancy/presence/motion), `covers` (cover), `shutter_auto`/`shutter_override` (binary_sensor ou switch) pour les paramètres par ouvrant. Pas de commande d’équipement.

Métadonnées par ouvrant existant : `shutter` = none/manual/connected (défaut none), `cover_entity` optionnel si connected, `auto_entity` et `override_entity` optionnels, `width`, `height`, `overhang_depth`, `overhang_gap` optionnels (mètres). Dimensions validées ; champs libres ne créent jamais une position de volet.

Racine `evolution` facultative : `voc_threshold`={value:number positif,unit:string exact du capteur}, `glazing_factor` number entre0et1 (défaut0.7, modèle estimé), `presence_delay_minutes` entre0et120 (défaut5). Aucun seuil COV si non choisi ou unité changée. Settings peut ajouter `pm25_action`=25 et `illuminance_low`=100 comme seuils historiques modifiables.

## Observations

Normalisation : pm25 vers µg/m³ (conversion mg/m³ uniquement), voc valeur numérique positive avec unité préservée (µg/m³, mg/m³, ppb, ppm, indice/index/ VOC index ou None pour indice explicite) ; jamais convertir concentration en indice. Illuminance lux lx. `purifier` boolean, `purifier_speed` % facultatif. `presence:<eid>` boolean dont `detail` indique motion vs occupancy/presence. `cover:<window_eid>` position % facultative ; `cover_state:<window_eid>` valeur string closed/open/opening/closing ; `shutter_auto:<eid>` / `shutter_override:<eid>` booleans. États non expirants, indisponibilité respectée ; mesures expirantes.

## Moteur

`assess(..., now=None, context=None)` dernier argument compatible. context facultatif contient les réglages evolution plus `opening_minutes`={window_eid:number|null}, `presence_off_minutes`={presence_eid:number|null}, `temperature_history` et `outdoor_history` listes de couples (iso UTC,value). Les durées ne proviennent pas de last_reported ; au démarrage un état déjà ouvert/absent reste de durée inconnue, puis est compté seulement depuis une transition connue reçue pendant la session. Historique borné en mémoire, pas de fausse pente après démarrage.

Extension additive `assessment.features` dictionnaire :
- `shutters`: liste par ouvrant {entity_id,mode,position:number|null,state:string|null,advice:'close'|'open'|null,message:string,shade_fraction:number|null,shade_model:'geometry'|'simple'|'unknown',manual_override:boolean|null,automatic:boolean|null}
- `presence`: {state:'occupied'|'empty'|'unknown'|'not_configured',message:string}
- `air`: {pm25_status:'high'|'ok'|'unknown'|'not_configured',voc_status:'high'|'ok'|'uninterpreted'|'unknown'|'not_configured',voc_unit:string|null,purifier:{on:boolean|null,speed:number|null},coverage:string,message:string}
- `ventilation`: {opened_minutes:number|null,duration_minutes:{min:number,max:number}|null,message:string,capacity:number|null}
- `humidity`: {dew_point:number|null,incoming_relative:number|null,glass_temperature:number|null,condensation_risk:boolean|null,message:string}
- `trends`: {indoor:number|null,outdoor:number|null,window_minutes:number,message:string}

Les règles de sécurité existantes gardent priorité. Un besoin PM2.5/COV haut ajoute un besoin d’air, sans faux seuil ni supprimer les contraintes. Purificateur ne résout pas CO₂. Présence vide adapte message/conseils, ne supprime aucune alerte ni besoin. La couleur reste liée aux besoins. Volet manuel conditionnel et position non mesurée ; dérogation connue respectée. Durée indicative ; buée, ombre et vitrage estimés. Les vues logement reprennent les mêmes besoins du moteur par pièce.

## Lots

1. Moteur : sources.py, assessment.py, engine/evolution.py et tests unitaires nouveaux. Tests d’abord.
2. Adaptation HA : const SOURCES, discovery, configuration, coordinator, health si nécessaire et tests correspondants. Tests d’abord.
3. Interface : frontend/model.ts et panel.ts, card/src/types.ts et views/panel.ts, view.ts si nécessaire ; tests UI modèles. Réemploi de la charte et de la carte ; pas de redesign.
4. Assemblage : tests Python, validations frontend/carte, banque de situations réelles du moteur, navigateur mobile/bureau, revue de code et des entrées utilisateur, documentation, version et compilation, commit Niakman13 seul, contrôles GitHub avant publication bêta.
