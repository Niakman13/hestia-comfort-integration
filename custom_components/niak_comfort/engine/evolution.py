"""Optional, explicitly estimated features for solar protection, airing and air.

No commands, inferred equipment state, or guaranteed air renewal are produced.
"""
from datetime import datetime, timedelta
import math


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _value(readings, key):
    r = readings.get(key)
    return r.value if r and r.usable else None


def _ventilation(readings):
    """A ventilation unit, possibly with a high-speed position: running if either position runs."""
    keys = [k for k in ('ventilation', 'ventilation_boost') if k in readings]
    if not keys:
        return None
    values = [_value(readings, k) for k in keys]
    on = True if any(v is True for v in values) else False if all(v is False for v in values) else None
    return {'on': on, 'boost': _value(readings, 'ventilation_boost') is True}


def air_features(readings, settings, context):
    def status(key, threshold):
        if key not in readings:
            return 'not_configured'
        value = _value(readings, key)
        return 'unknown' if value is None else 'high' if value >= threshold else 'ok'
    pm = status('pm25', settings.pm25_action)
    purifier_on = _value(readings, 'purifier') is True
    # A running purifier is the remedy for particles: they no longer call for opening.
    pm_treated = pm == 'high' and purifier_on
    voc, threshold = readings.get('voc'), context.get('voc_threshold')
    vs = 'not_configured' if voc is None else 'unknown' if not voc.usable else 'uninterpreted'
    if (voc and voc.usable and isinstance(threshold, dict) and _number(threshold.get('value'))
            and threshold['value'] > 0 and isinstance(threshold.get('unit'),str) and threshold['unit'] == (voc.unit or '')):
        vs = 'high' if voc.value >= threshold['value'] else 'ok'
    covered = [label for key, label in (('co2','CO₂'),('pm25','PM2.5'),('voc','COV')) if _value(readings,key) is not None]
    missing = [label for key, label in (('co2','CO₂'),('pm25','PM2.5'),('voc','COV')) if _value(readings,key) is None]
    coverage = 'Mesures disponibles : ' + (', '.join(covered) or 'aucune')
    if missing:
        coverage += ' ; non suivies ou indisponibles : ' + ', '.join(missing)
    messages = []
    if pm == 'high': messages.append('PM2.5 élevées : le purificateur les filtre.' if pm_treated else 'PM2.5 élevées : besoin d’air maintenu sous réserve des conditions extérieures.')
    if vs == 'high': messages.append('COV au-dessus du seuil choisi : besoin d’air maintenu.')
    if vs == 'uninterpreted': messages.append('COV mesurés, interprétation indisponible sans seuil de même unité.')
    if 'purifier' in readings:
        messages.append('Le purificateur ne renouvelle pas l’air et ne retire pas le CO₂ ; son action sur les COV n’est pas présumée.')
    return dict(pm25_status=pm,voc_status=vs,voc_unit=voc.unit if voc else None,
                purifier={'on':_value(readings,'purifier'),'speed':_value(readings,'purifier_speed')},pm25_treated=pm_treated,
                ventilation=_ventilation(readings),
                coverage=coverage,message=' '.join(messages) or 'Les mesures d’air restent distinctes.')


def _presence(readings, context):
    sources = {k.split(':',1)[1]:r for k,r in readings.items() if k.startswith('presence:')}
    if not sources:
        return {'state':'not_configured','message':'Présence non suivie.'}
    state = 'unknown'
    if any(r.usable and r.value is True for r in sources.values()):
        state = 'occupied'
    else:
        delay = context.get('presence_delay_minutes',5)
        delay = delay if _number(delay) and 0 <= delay <= 120 else 5
        times = context.get('presence_off_minutes') or {}
        if all(r.usable and r.value is False and r.detail in ('occupancy','presence')
               and _number(times.get(e)) and times[e] >= delay for e,r in sources.items()):
            state = 'empty'
    return {'state':state,'message':{'occupied':'Présence détectée.', 'empty':'Pièce confirmée vide : suivi du confort et de l’air conservé ; vérifiez les fenêtres ouvertes.',
                                   'unknown':'Présence inconnue ; le silence d’un détecteur de mouvement ne prouve pas l’absence.'}[state]}


def _shade(meta, sun):
    from .assessment import EXPOSURES
    if sun is None or meta.exposure not in EXPOSURES:
        return None, 'unknown'
    gap = math.radians(((sun.azimuth-EXPOSURES[meta.exposure]+540)%360)-180)
    facing = math.cos(gap)
    if sun.elevation <= 0 or facing <= 0:
        return 1.0, 'simple'
    if (all(_number(v) for v in (meta.height,meta.overhang_depth,meta.overhang_gap))
            and meta.height > 0 and meta.overhang_depth >= 0 and meta.overhang_gap >= 0):
        shadow = meta.overhang_depth * math.tan(math.radians(min(sun.elevation,89.9))) / facing
        return round(max(0,min(1,(shadow-meta.overhang_gap)/meta.height)),2), 'geometry'
    return (round(1-1/3,2) if meta.sheltered else 0.0), 'simple'


def _shutters(readings, settings, openings, sun, details, needs):
    by_id={d['entity_id']:d for d in details}
    result=[]
    for eid,meta in openings.items():
        if meta.shutter not in ('manual','connected'):
            continue
        shade,model = _shade(meta,sun)
        d=by_id.get(eid,{})
        watts=d.get('sun_wm2')
        # Details already apply the historical simple shelter attenuation. Geometry
        # replaces it here rather than attenuating the same facade twice.
        if model == 'geometry':
            from .assessment import facade_share, facade_irradiance
            watts=facade_irradiance(facade_share(meta.exposure,sun),sun,_value(readings,'solar'))
            if watts is not None: watts *= 1-shade
        position = _value(readings,'cover:'+eid) if meta.shutter == 'connected' else None
        state = _value(readings,'cover_state:'+eid) if meta.shutter == 'connected' else None
        override=_value(readings,'shutter_override:'+meta.override_entity) if meta.override_entity else None
        automatic=_value(readings,'shutter_auto:'+meta.auto_entity) if meta.auto_entity else None
        # Adaptive Cover Pro knows whether the sun really stands in front of this window (its field of view).
        driven=meta.driver=='adaptive_cover_pro'
        front=_value(readings,'shutter_sun:'+eid) if driven else None
        target=_value(readings,'shutter_target:'+eid) if driven else None
        strong=watts is not None and watts >= settings.sun_facade
        if front is False: strong=False
        elif front is True and watts is None: strong=True
        advice=None
        message='Position non mesurée.' if position is None else f'Position mesurée : {position:g} %.'
        manual=meta.shutter == 'manual'
        tip=''
        if override is True:
            message += ' Dérogation active respectée.'
        elif strong and 'cool' in needs and position != 0 and state != 'closed':
            advice='close'
            tip=' Si le volet est ouvert, fermez-le pour limiter les apports solaires.' if manual else ' Fermez le volet exposé pour limiter les apports solaires.'
        elif strong and 'heat' in needs and position != 100 and state != 'open':
            advice='open'
            tip=' Si le volet est fermé, ouvrez-le pour profiter du soleil.' if manual else ' Ouvrez le volet pour profiter du soleil.'
        elif sun is not None and sun.elevation < 0 and 'heat' in needs and position != 0 and state != 'closed':
            advice='close'
            tip=' Si le volet est ouvert, fermez-le pour protéger la pièce du froid nocturne.' if manual else ' Fermez le volet pour protéger la pièce du froid nocturne.'
        if driven and override is not True:
            if automatic is True:
                # It moves the cover itself: Niak does not ask the person to do it twice.
                advice,tip=None,' Adaptive Cover Pro pilote le volet' + (f', position visée {target:g} %.' if target is not None else '.')
            elif automatic is False and advice:
                tip += ' Le pilotage automatique d’Adaptive Cover Pro est coupé.'
        message += tip
        if model == 'geometry': message += ' Ombre estimée par géométrie.'
        elif model == 'simple': message += ' Ombre estimée par modèle simple.'
        light=_value(readings,'illuminance')
        if light is not None and light < settings.illuminance_low:
            message += ' Luminosité intérieure faible ; elle ne prouve pas la position du volet.'
        result.append(dict(entity_id=eid,mode=meta.shutter,position=position,state=state,advice=advice,message=message,
                           shade_fraction=shade,shade_model=model,manual_override=override,automatic=automatic,
                           cover=meta.cover_entity,driver=meta.driver,sun_front=front,target=target,
                           sun_start=_value(readings,'shutter_sun_start:'+eid) if driven else None,
                           sun_end=_value(readings,'shutter_sun_end:'+eid) if driven else None))
    return result


def _slope(history, now, window=30):
    if now is None or now.tzinfo is None:
        return None
    points={}
    for point in history or []:
        try:
            stamp,value=point
            stamp=datetime.fromisoformat(stamp.replace('Z','+00:00')) if isinstance(stamp,str) else stamp
            if stamp.tzinfo and _number(value) and now-timedelta(minutes=window) <= stamp <= now:
                points[stamp]=value
        except (ValueError,TypeError,AttributeError):
            continue
    values=sorted(points.items())
    if len(values)<3 or (values[-1][0]-values[0][0]).total_seconds()<600:
        return None
    xs=[(t-values[0][0]).total_seconds()/3600 for t,v in values]
    ys=[v for t,v in values]
    mx,my=sum(xs)/len(xs),sum(ys)/len(ys)
    denominator=sum((x-mx)**2 for x in xs)
    return round(sum((x-mx)*(y-my) for x,y in zip(xs,ys))/denominator,2) if denominator else None


def features(readings,settings,context,openings,sun,details,needs,action,reason,now,ai,ae,air):
    ti,te=_value(readings,'indoor_temperature'),_value(readings,'outdoor_temperature')
    rh=_value(readings,'indoor_humidity')
    dew=None
    if ti is not None and rh is not None and rh>0:
        alpha=math.log(rh/100)+17.62*ti/(243.12+ti)
        dew=round(243.12*alpha/(17.62-alpha),1)
    glazing=context.get('glazing_factor',.7)
    glazing=glazing if _number(glazing) and 0<=glazing<=1 else .7
    glass=round(te+glazing*(ti-te),1) if ti is not None and te is not None else None
    from .assessment import absolute_humidity
    saturated=absolute_humidity(ti,100) if ti is not None else None
    incoming=round(ae/saturated*(273.15+te)/(273.15+ti)*100,1) if ae is not None and saturated and te is not None else None
    condensation=dew >= glass if dew is not None and glass is not None else None
    hmessage='Buée estimée à partir du point de rosée et d’un vitrage modélisé ; aucune condensation observée.'
    if ai is not None and ae is not None and ae>ai+1:
        hmessage+=' L’air extérieur risque de réhumidifier la pièce.'
    opened=[d['entity_id'] for d in details if d['open'] is True]
    minutes=context.get('opening_minutes') or {}
    # If even one open contact lacks a reliable transition, the room duration is unknown.
    elapsed=max(minutes[e] for e in opened) if opened and all(_number(minutes.get(e)) and minutes[e]>=0 for e in opened) else None
    from .wind import open_first, crossing
    candidates=opened if opened else open_first(details) if action == "ouvrir" else []
    capacities=[]
    for eid in candidates:
        e=openings.get(eid)
        if e is None:
            capacities.append(None)
            continue
        if _number(e.width) and _number(e.height) and e.width>0 and e.height>0:
            capacities.append(e.width*e.height*{'window':.6,'french':.8,'skylight':.25,'door':.8}.get(e.kind,.5))
        else:
            capacities.append(None)
    capacity=round(sum(capacities),2) if capacities and all(v is not None for v in capacities) else None
    duration=None
    if needs and (action=='ouvrir' or (opened and action=='ok')):
        middle=10
        if ti is not None and te is not None and abs(ti-te)>=8: middle=5
        selected=[dict(d,open=True) for d in details if d['entity_id'] in candidates]
        if crossing(selected) == 'wind': middle*=.75
        if capacity is not None: middle/=max(.5,min(2,capacity))
        if reason=='short_air_change': middle=min(middle,5)
        duration={'min':max(2,round(middle*.6)),'max':max(3,round(middle*1.5))}
    vm='Durée indicative avant réévaluation ; les mesures restent prioritaires, sans garantie de renouvellement complet.'
    if capacity is not None: vm+=' Capacité estimée en m² effectifs, avec hypothèse d’ouverture ; débit non mesuré.'
    if opened and elapsed is None: vm+=' Ouvert depuis une durée inconnue.'
    return dict(shutters=_shutters(readings,settings,openings,sun,details,needs),presence=_presence(readings,context),air=air,
                ventilation=dict(opened_minutes=elapsed,duration_minutes=duration,message=vm,capacity=capacity),
                humidity=dict(dew_point=dew,incoming_relative=incoming,glass_temperature=glass,condensation_risk=condensation,message=hmessage),
                trends=dict(indoor=_slope(context.get('temperature_history'),now),outdoor=_slope(context.get('outdoor_history'),now),window_minutes=30,
                            message='Tendance en °C/h sur au plus 30 minutes de mesures réelles ; au moins 3 mesures sur 10 minutes.'))
