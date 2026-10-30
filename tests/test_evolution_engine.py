"""Replayed safety and uncertainty cases for blocks 7–9."""
from datetime import timedelta
import unittest
from test_engine import NOW, zone
from engine.assessment import Opening, Sun, assess
from engine.sources import Reading, normalize


class EvolutionTests(unittest.TestCase):
    def test_manual_wood_is_conditional_and_not_measured(self):
        r = assess(zone(indoor_temperature=28, solar=700), openings={'a': Opening(exposure='O', shutter='manual')}, sun=Sun(30,270))
        s = r.features['shutters'][0]
        self.assertEqual(s['advice'], 'close')
        self.assertIsNone(s['position'])
        self.assertIn('Si', s['message'])
    def test_pm25_adds_need_but_preserves_pollution_veto(self):
        r = assess(zone(pm25=80, pollution=True))
        self.assertIn('air',r.needs)
        self.assertEqual(r.action,'attendre')
    def test_voc_needs_matching_unit_and_user_threshold(self):
        q=zone(); q['voc']=Reading(500,'valid','sensor.voc',unit='ppb')
        self.assertEqual(assess(q).features['air']['voc_status'],'uninterpreted')
        self.assertNotIn('air',assess(q,context={'voc_threshold':{'value':100,'unit':'ppm'}}).needs)
        self.assertIn('air',assess(q,context={'voc_threshold':{'value':100,'unit':'ppb'}}).needs)
    def test_motion_off_does_not_confirm_absence(self):
        q=zone(); q['presence:binary_sensor.m']=Reading(False,'valid','binary_sensor.m',detail='motion')
        self.assertEqual(assess(q,context={'presence_off_minutes':{'binary_sensor.m':20}}).features['presence']['state'],'unknown')
    def test_occupancy_off_requires_known_delay_and_all_sources(self):
        q=zone(); q['presence:binary_sensor.o']=Reading(False,'valid','binary_sensor.o',detail='occupancy')
        self.assertEqual(assess(q).features['presence']['state'],'unknown')
        r=assess(q,context={'presence_off_minutes':{'binary_sensor.o':6}})
        self.assertEqual(r.features['presence']['state'],'empty')
        q['presence:binary_sensor.m']=Reading(None,'unknown','binary_sensor.m',detail='motion')
        self.assertEqual(assess(q,context={'presence_off_minutes':{'binary_sensor.o':6}}).features['presence']['state'],'unknown')
    def test_open_duration_unknown_without_transition(self):
        q=zone(**{'window:a':True})
        self.assertIsNone(assess(q).features['ventilation']['opened_minutes'])
        self.assertEqual(assess(q,context={'opening_minutes':{'a':12}}).features['ventilation']['opened_minutes'],12)
    def test_override_suppresses_shutter_instruction(self):
        q=zone(indoor_temperature=28,solar=700); q['shutter_override:switch.override']=Reading(True,'valid','switch.override')
        r=assess(q,openings={'a':Opening(exposure='O',shutter='connected',override_entity='switch.override')},sun=Sun(30,270))
        self.assertIsNone(r.features['shutters'][0]['advice'])
    def test_humid_air_cannot_claim_drying(self):
        r=assess(zone(indoor_temperature=26,indoor_humidity=65,outdoor_temperature=24,outdoor_humidity=95,**{'window:a':True}))
        self.assertGreater(r.features['humidity']['incoming_relative'],65)
        self.assertEqual(r.reason,'rehumidification_risk')
    def test_history_needs_time_coverage(self):
        ctx={'temperature_history':[(NOW.isoformat(),22),((NOW+timedelta(minutes=1)).isoformat(),24)]}
        self.assertIsNone(assess(zone(),now=NOW+timedelta(minutes=1),context=ctx).features['trends']['indoor'])
    def test_pm25_normalization_and_invalid_units(self):
        def n(kind,v,u): return normalize(kind,v,u,source='sensor.x',now=NOW,reported_at=NOW)
        self.assertEqual(n('pm25',.03,'mg/m³').value,30)
        self.assertFalse(n('pm25',10,'ppm').usable)
        self.assertEqual(n('voc',200,'ppb').unit,'ppb')
        self.assertEqual(n('illuminance',30,'lx').unit,'lx')
        self.assertEqual(n('cover_state','closed',None).value,'closed')
    def test_geometry_shade_and_unavailable_position(self):
        r=assess(zone(solar=700),openings={'a':Opening(exposure='S',shutter='connected',height=1,overhang_depth=2,overhang_gap=0)},sun=Sun(60,180))
        s=r.features['shutters'][0]
        self.assertEqual(s['shade_model'],'geometry')
        self.assertEqual(s['shade_fraction'],1)
        self.assertIsNone(s['position'])
    def test_purifier_does_not_erase_co2(self):
        r=assess(zone(co2=1800,purifier=True))
        self.assertIn('air',r.needs)
        self.assertEqual(r.level,'urgent')
        self.assertIn('CO₂',r.features['air']['message'])

    def test_known_duration_does_not_erase_measured_air_need(self):
        r=assess(zone(co2=1800,**{'window:a':True}),context={'opening_minutes':{'a':90}})
        self.assertIn('air',r.needs)
        self.assertEqual(r.features['ventilation']['opened_minutes'],90)
        self.assertIsNotNone(r.features['ventilation']['duration_minutes'])
    def test_unknown_contact_makes_whole_open_duration_unknown(self):
        r=assess(zone(**{'window:a':True,'window:b':True}),context={'opening_minutes':{'a':12}})
        self.assertIsNone(r.features['ventilation']['opened_minutes'])
    def test_thermal_need_and_presence_independent(self):
        q=zone(indoor_temperature=29); q['presence:o']=Reading(False,'valid','binary_sensor.o',detail='occupancy')
        r=assess(q,context={'presence_off_minutes':{'o':30}})
        self.assertIn('cool',r.needs)
        self.assertEqual(r.features['presence']['state'],'empty')
    def test_cold_sun_opportunity_is_separate_from_contact_action(self):
        r=assess(zone(indoor_temperature=18,solar=700),openings={'a':Opening(exposure='S',shutter='manual')},sun=Sun(30,180))
        self.assertEqual(r.features['shutters'][0]['advice'],'open')
        self.assertEqual(r.action,'ok')
        self.assertEqual(r.reason,'heat_needed')
    def test_night_protection_and_no_shutter(self):
        q=zone(indoor_temperature=18)
        self.assertEqual(assess(q,openings={'a':Opening(shutter='manual')},sun=Sun(-10,180)).features['shutters'][0]['advice'],'close')
        self.assertEqual(assess(q,openings={'a':Opening()},sun=Sun(-10,180)).features['shutters'],[])
    def test_any_driver_is_named_when_it_drives(self):
        o={'a':Opening(exposure='O',shutter='connected',cover_entity='cover.v',auto_entity='switch.auto',driver='cover_extender')}
        q=zone(indoor_temperature=28,solar=700); q['cover:a']=Reading(100,'valid','cover.v'); q['shutter_auto:switch.auto']=Reading(True,'valid','switch.auto')
        s=assess(q,openings=o,sun=Sun(30,270)).features['shutters'][0]
        self.assertIsNone(s['advice']); self.assertIn('Cover Extender pilote le volet',s['message'])
    def test_adaptive_cover_pro_drives_or_is_switched_off(self):
        o={'a':Opening(exposure='O',shutter='connected',cover_entity='cover.v',auto_entity='switch.auto',driver='adaptive_cover_pro')}
        def run(auto,front):
            q=zone(indoor_temperature=28,solar=700); q['cover:a']=Reading(100,'valid','cover.v')
            q['shutter_auto:switch.auto']=Reading(auto,'valid','switch.auto'); q['shutter_sun:a']=Reading(front,'valid','binary_sensor.s')
            q['shutter_target:a']=Reading(20,'valid','sensor.t')
            return assess(q,openings=o,sun=Sun(30,270)).features['shutters'][0]
        s=run(True,True)
        self.assertIsNone(s['advice']); self.assertIn('Adaptive Cover Pro pilote',s['message']); self.assertEqual(s['target'],20)
        s=run(False,True)
        self.assertEqual(s['advice'],'close'); self.assertIn('coupé',s['message']); self.assertTrue(s['sun_front'])
        # Out of its field of view, the sun does not reach the window: nothing to close.
        self.assertIsNone(run(False,False)['advice'])
        # Automatic control on, but its sun tracking is off: it is not really driving.
        q=zone(indoor_temperature=28,solar=700); q['cover:a']=Reading(100,'valid','cover.v')
        q['shutter_auto:switch.auto']=Reading(True,'valid','switch.auto'); q['shutter_sun:a']=Reading(True,'valid','binary_sensor.s')
        q['shutter_tracking:a']=Reading(False,'valid','switch.t')
        s=assess(q,openings=o,sun=Sun(30,270)).features['shutters'][0]
        self.assertEqual((s['advice'],s['off'],s['driving']),('close','tracking',False)); self.assertIn('suivi du soleil',s['message'])
        # Without its detection, its override signal says nothing.
        o2={'a':Opening(exposure='O',shutter='connected',cover_entity='cover.v',override_entity='binary_sensor.o',driver='adaptive_cover_pro')}
        q=zone(indoor_temperature=28,solar=700); q['cover:a']=Reading(100,'valid','cover.v')
        q['shutter_override:binary_sensor.o']=Reading(True,'valid','binary_sensor.o'); q['shutter_detection:a']=Reading(False,'valid','switch.d')
        self.assertIsNone(assess(q,openings=o2,sun=Sun(30,270)).features['shutters'][0]['manual_override'])
    def test_sun_arriving_soon_closes_before_and_exact_bearing_counts(self):
        o={'a':Opening(shutter='connected',cover_entity='cover.v',auto_entity='switch.auto',driver='adaptive_cover_pro',azimuth=273)}
        q=zone(indoor_temperature=28); q['cover:a']=Reading(100,'valid','cover.v'); q['shutter_auto:switch.auto']=Reading(False,'valid','switch.auto')
        q['shutter_sun:a']=Reading(False,'valid','binary_sensor.s'); q['shutter_sun_start:a']=Reading((NOW+timedelta(minutes=50)).isoformat(),'valid','sensor.s')
        s=assess(q,openings=o,sun=Sun(30,200),now=NOW).features['shutters'][0]
        self.assertEqual(s['advice'],'close'); self.assertTrue(s['soon']); self.assertIn('arrive sur la fenêtre',s['message'])
        q['shutter_sun_start:a']=Reading((NOW+timedelta(hours=5)).isoformat(),'valid','sensor.s')
        self.assertIsNone(assess(q,openings=o,sun=Sun(30,200),now=NOW).features['shutters'][0]['advice'])
        from engine.assessment import facade_share
        self.assertGreater(facade_share(None,Sun(30,273),273),facade_share('S',Sun(30,273)))
    def test_trend_uses_real_timed_history(self):
        ctx={'temperature_history':[((NOW-timedelta(minutes=20)).isoformat(),20),((NOW-timedelta(minutes=10)).isoformat(),21),(NOW.isoformat(),22)]}
        self.assertEqual(assess(zone(),now=NOW,context=ctx).features['trends']['indoor'],6)
    def test_tile_curves_say_the_way_and_the_last_half_hour(self):
        at=lambda m,v:((NOW-timedelta(minutes=m)).isoformat(),v)
        ctx={'humidity_history':[at(m,66) for m in (28,20,12,4)],'voc_history':[at(28,380),at(20,340),at(12,300),at(4,270),at(45,500)],
             'co2_history':[at(5,600),at(1,610)]}
        c=assess(zone(),now=NOW,context=ctx).features['trends']['curves']
        self.assertEqual(c['humidity']['way'],'stable')
        self.assertEqual(c['voc']['way'],'down')
        # The oldest point first, as [minutes ago, value]; what is older than half an hour is left out.
        self.assertEqual([p[1] for p in c['voc']['points']],[380,340,300,270])
        self.assertEqual(c['voc']['points'][0][0],29)
        # Under ten minutes of measures: no way said.
        self.assertIsNone(c['co2']); self.assertIsNone(c['temperature'])
    def test_durations_with_hard_veto_unavailable(self):
        r=assess(zone(co2=1800,rain=True,**{'window:a':True}),context={'opening_minutes':{'a':10}})
        self.assertEqual(r.action,'fermer')
        self.assertIsNone(r.features['ventilation']['duration_minutes'])
    def test_measurements_expire_states_hold_until_unavailable(self):
        for kind,value,unit in [('presence','off',None),('position',50,'%'),('switch','on',None)]:
            self.assertTrue(normalize(kind,value,unit,source='sensor.x',now=NOW,reported_at=NOW-timedelta(days=4)).usable)
        self.assertFalse(normalize('pm25',30,'µg/m³',source='sensor.x',now=NOW,reported_at=NOW-timedelta(days=4)).usable)
    def test_condensation_named_estimated_and_not_observed(self):
        r=assess(zone(indoor_temperature=22,indoor_humidity=80,outdoor_temperature=0))
        self.assertTrue(r.features['humidity']['condensation_risk'])
        self.assertIn('estimée',r.features['humidity']['message'])
    def test_geometric_shade_also_applies_to_main_opening(self):
        r=assess(zone(indoor_temperature=28,solar=700,**{'window:a':True}),openings={'a':Opening(exposure='S',height=1,overhang_depth=2,overhang_gap=0)},sun=Sun(60,180))
        self.assertEqual(r.openings[0]['sun_wm2'],0)
        self.assertNotIn('sun_entering',r.openings[0]['flags'])

    def test_airing_capacity_excludes_closed_windows(self):
        r=assess(zone(co2=1500,**{'window:a':True,'window:b':False}),openings={'a':Opening(width=1,height=1),'b':Opening(width=5,height=5)})
        self.assertEqual(r.features['ventilation']['capacity'],.6)
    def test_incoming_rh_accounts_for_temperature_expansion(self):
        r=assess(zone(indoor_temperature=22,outdoor_temperature=10,outdoor_humidity=80))
        expected=80*__import__('math').exp(17.67*10/(10+243.5)-17.67*22/(22+243.5))
        self.assertAlmostEqual(r.features['humidity']['incoming_relative'],expected,delta=.1)
    def test_voc_high_and_unknown_rain_keeps_need_and_blocks_advice(self):
        q=zone(rain=None); q['voc']=Reading(600,'valid','sensor.voc',unit='ppb')
        r=assess(q,context={'voc_threshold':{'value':100,'unit':'ppb'}})
        self.assertIn('air',r.needs)
        self.assertEqual(r.action,'unknown')
    def test_no_threshold_from_dimensionless_unit(self):
        q=zone(); q['voc']=Reading(600,'valid','sensor.voc')
        self.assertEqual(assess(q,context={'voc_threshold':{'value':100,'unit':None}}).features['air']['voc_status'],'uninterpreted')

class UnitlessIndexTests(unittest.TestCase):
    def test_explicit_unitless_voc_index_uses_only_its_bound_threshold(self):
        from engine.assessment import assess
        from engine.sources import Reading
        rows={'indoor_temperature':Reading(23,'valid'),'outdoor_temperature':Reading(20,'valid'),
              'voc':Reading(180,'valid',unit=None)}
        result=assess(rows, context={'voc_threshold':{'value':160,'unit':''}})
        self.assertEqual(result.features['air']['voc_status'],'high')
        result=assess({**rows,'voc':Reading(180,'valid',unit='ppb')}, context={'voc_threshold':{'value':160,'unit':''}})
        self.assertEqual(result.features['air']['voc_status'],'uninterpreted')

class SeparatePollutantVerdicts(unittest.TestCase):
    def test_particles_do_not_make_the_co2_measure_high(self):
        a=assess(zone(co2=500,pm25=80))
        self.assertIn('air',a.needs)
        self.assertEqual(a.features['air']['co2_status'],'ok')
        self.assertEqual(a.features['air']['pm25_status'],'high')
        self.assertEqual(assess(zone(co2=None,pm25=80)).features['air']['co2_status'],'unknown')

    def test_particle_need_does_not_start_co2_hysteresis(self):
        previous=assess(zone(co2=500,pm25=80))
        result=assess(zone(co2=1150,pm25=0),previous=previous)
        self.assertEqual(result.features['air']['co2_status'],'ok')
        self.assertNotIn('air',result.needs)
