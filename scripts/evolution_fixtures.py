"""Replay the approved evolution situations through the real room/home engines."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'custom_components/niak_comfort'))
from engine.assessment import assess, Opening, Sun
from engine.sources import normalize
from engine.home import synthesis
now = datetime.now(timezone.utc)
WINDOW = 'binary_sensor.demo_window'
PRESENCE = 'binary_sensor.demo_presence'

def scene(key, title, *, ti=27, te=31, co2=850, hi=50, he=50, opened=False,
          shutter='manual', sun=None, shade=False, extras=None, context=None):
    rows={}
    for name,kind,value,unit in [('indoor_temperature','temperature',ti,'°C'),('outdoor_temperature','temperature',te,'°C'),
        ('indoor_humidity','humidity',hi,'%'),('outdoor_humidity','humidity',he,'%'),('co2','co2',co2,'ppm'),
        ('rain','rain',False,None),('pollution','pollution',False,None),('wind_gust','wind',5,'km/h'),
        ('solar','irradiance',700,'W/m²')]:
        rows[name]=normalize(kind,value,unit,source='sensor.demo_'+name,reported_at=now,now=now)
    rows['window:'+WINDOW]=normalize('window',opened,source=WINDOW,reported_at=now,now=now,max_age=None)
    rows['presence:'+PRESENCE]=replace(normalize('presence',True,source=PRESENCE,reported_at=now,now=now,max_age=None),detail='occupancy')
    for name,(kind,value,unit,detail) in (extras or {}).items():
        r=normalize(kind,value,unit,source='sensor.demo_'+name.replace(':','_'),reported_at=now,now=now,max_age=None if kind in ('presence','purifier','switch','cover_state') else 1800)
        rows[name]=replace(r,detail=detail) if detail else r
    meta=Opening(exposure='S' if shade or key=='winter' else 'O',shutter=shutter,
        auto_entity='binary_sensor.demo_auto' if key=='override' else None,override_entity='binary_sensor.demo_override' if key=='override' else None,
        width=1.2,height=2.15,overhang_depth=1.0 if shade else None,overhang_gap=0.2 if shade else None)
    a=assess(rows,openings={WINDOW:meta},sun=sun or Sun(35,270),now=now,context=context or {})
    view={'version':1,'entry_id':'demo-salon','area_id':'demo-salon','title':'Salon','computed_at':now.isoformat(),
          'assessment':a.to_dict(),'observations':{k:asdict(r) for k,r in rows.items()},'names':{WINDOW:'Fenêtre ouest'},
          'floor':{'floor_id':'rdc','name':'Rez-de-chaussée','level':0},'comfort_minimum':20}
    return {'id':key,'title':title,'view':view,'home':synthesis([view])}

scenes=[
 scene('manual','Chaleur · volets manuels bois'),
 scene('none','Chaleur · aucun volet',shutter='none'),
 scene('override','Volet connecté · dérogation',shutter='connected',extras={
  'cover:'+WINDOW:('position',60,'%',None),'cover_state:'+WINDOW:('cover_state','open',None,None),
  'shutter_auto:binary_sensor.demo_auto':('switch',True,None,None),'shutter_override:binary_sensor.demo_override':('switch',True,None,None)}),
 scene('winter','Froid · soleil utile',ti=18.5,te=9,sun=Sun(20,180)),
 scene('shade','Débord de toit · ombre estimée',ti=23,te=29,sun=Sun(70,180),shade=True),
 scene('night','Nuit · préservez la chaleur',ti=18.5,te=7,sun=Sun(-10,270)),
 scene('co2','CO₂ élevé · aération à commencer',ti=24,te=19,co2=1700),
 scene('airing','Aération engagée · CO₂ encore élevé',ti=23.5,te=19,co2=1650,opened=True,context={'opening_minutes':{WINDOW:8},'temperature_history':[((now-timedelta(minutes=30)).isoformat(),23.8),((now-timedelta(minutes=15)).isoformat(),23.65),(now.isoformat(),23.5)]}),
 scene('empty','Pièce vide · fenêtre ouverte',ti=22,te=14,opened=True,context={'opening_minutes':{WINDOW:25},'presence_off_minutes':{PRESENCE:25}},extras={'presence:'+PRESENCE:('presence',False,None,'occupancy')}),
 scene('motion','Mouvement silencieux · présence inconnue',ti=23,te=20,extras={'presence:'+PRESENCE:('presence',False,None,'motion')}),
 scene('particles','Particules · extérieur défavorable',ti=25,te=21,extras={'pm25':('pm25',38,'µg/m³',None),'pollution':('pollution',True,None,None),'purifier':('purifier',True,None,None),'purifier_speed':('percentage',65,'%',None)}),
 scene('purifier','Purificateur en marche · CO₂ élevé',ti=23,te=19,co2=1700,extras={'purifier':('purifier',True,None,None),'purifier_speed':('percentage',70,'%',None)}),
 scene('voc','COV · indice sans seuil compatible',ti=23,te=21,extras={'voc':('voc',180,'VOC index',None)}),
 scene('humidity','Aération qui réhumidifie',ti=22,te=21,hi=55,he=75,opened=True,context={'opening_minutes':{WINDOW:18}}),
 scene('condensation','Vitrage · risque de buée estimé',ti=20,te=4,hi=70,he=70,context={'glazing_factor':0.6}),
 scene('missing','Contact restauré · durée inconnue',ti=23,te=None,opened=True,extras={'presence:'+PRESENCE:('presence',None,None,'occupancy')})
]
out=ROOT/'card/preview/evolution/real-fixtures.json'
out.write_text(json.dumps(scenes,ensure_ascii=False,indent=2)+'\n')
print(out)
