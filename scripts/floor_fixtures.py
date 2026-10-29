"""Generate fictional home views using the real room and home engines."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'custom_components/hestia_comfort'))
from engine.assessment import assess, Opening
from engine.sources import normalize
from engine.home import synthesis
now=datetime.now(timezone.utc)

def room(name,t,level,exposure,*,missing=False,outside=20,gust=5,opened=False,bearing=None):
    entity='binary_sensor.'+name.lower().replace(' ','_')
    readings={k:normalize(kind,val,unit,source='sensor.demo_'+k,reported_at=now,now=now) for k,kind,val,unit in
        [('indoor_temperature','temperature',None if missing else t,'°C'),('outdoor_temperature','temperature',outside,'°C'),
         ('rain','rain',False,None),('pollution','pollution',False,None),('wind_gust','wind',gust,'km/h')]}
    readings['window:'+entity]=normalize('window',opened,source=entity,reported_at=now,now=now)
    if bearing is not None:readings['wind_bearing']=normalize('bearing',bearing,'°',source='sensor.wind',reported_at=now,now=now)
    return {'version':1,'entry_id':name,'title':name,'area_id':None,'computed_at':now.isoformat(),
        'floor':None if level is None else {'floor_id':str(level),'name':'Rez-de-chaussée' if level==0 else 'Étage '+str(level),'level':level},
        'comfort_minimum':20,'assessment':assess(readings,openings={entity:Opening(exposure=exposure)}).to_dict(),
        'observations':{k:asdict(v) for k,v in readings.items()},'names':{entity:'Fenêtre '+name}}
scenarios=[]
for key,title in [('stack','Deux niveaux, sans vent'),('plain','Maison de plain-pied'),('missing','Mesure absente en haut'),('unknown','Étages non renseignés'),('gust','Rafales : ouverture bloquée'),('hot','Extérieur plus chaud'),('open','Ouvertures engagées'),('third','Trois niveaux'),('wind','Vent compatible')]:
    options={'outside':30} if key=='hot' else {'gust':70} if key=='gust' else {'opened':True} if key=='open' else {'bearing':270} if key=='wind' else {}
    upper=0 if key=='plain' else None if key=='unknown' else 1
    rooms=[room('Salon',24, None if key=='unknown' else 0,'O',**options),room('Cuisine',25,None if key=='unknown' else 0,'S',**options),room('Chambre A',27,upper,'E',**options),room('Chambre M',28,upper,'E',missing=key=='missing',**options)]
    if key=='third':rooms.append(room('Bureau',29,2,'N'))
    scenarios.append({'id':key,'title':title,'event':{'version':1,'rooms':rooms,'home':synthesis(rooms)}})
(ROOT/'card/preview/floors.json').write_text(json.dumps(scenarios,ensure_ascii=False,indent=2)+'\n')
