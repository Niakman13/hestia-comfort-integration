"""The comfort review: hours graded on the categories of EN 16798-1, rooms graded on what they measure."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import review

PARIS = ZoneInfo("Europe/Paris")


def hourly(start, days, value):
    """`days` of hourly values from `start`: a number, or a function of the time."""
    return [(start + timedelta(hours=h), value(start + timedelta(hours=h)) if callable(value) else value) for h in range(days * 24)]


JANUARY = datetime(2026, 1, 1, tzinfo=timezone.utc)
JULY = datetime(2026, 7, 1, tzinfo=timezone.utc)


class Categories(unittest.TestCase):
    def test_winter_uses_the_fixed_ranges_for_dwellings(self):
        outdoor = hourly(JANUARY, 30, 6.0)
        normal = review.room({"temperature": hourly(JANUARY, 30, 20.5)}, outdoor)
        self.assertEqual((normal["themes"]["warmth"]["score"], normal["themes"]["warmth"]["letter"]), (75, "B"))
        # 19 °C, the legal mean for heating, is moderate comfort: half the points, not none.
        moderate = review.room({"temperature": hourly(JANUARY, 30, 19.0)}, outdoor)
        self.assertEqual((moderate["themes"]["warmth"]["score"], moderate["themes"]["warmth"]["letter"]), (50, "D"))
        self.assertEqual(review.room({"temperature": hourly(JANUARY, 30, 17.0)}, outdoor)["themes"]["warmth"]["score"], 0)

    def test_a_summer_without_cooling_follows_the_weather(self):
        """Salon in July: 26-28 °C after hot days is within the standard for a house without air conditioning."""
        outdoor = hourly(JULY - timedelta(days=10), 40, 27.0)
        warm = review.room({"temperature": hourly(JULY, 30, 27.5)}, outdoor)["themes"]["warmth"]
        self.assertEqual(warm["letter"], "A")
        self.assertEqual(warm["monthly"][0]["hot"], 0)
        # The same 27.5 °C in a cool spell, running mean under 10 °C: the fixed ranges apply, and it is too hot.
        cool = review.room({"temperature": hourly(JULY, 30, 27.5)}, hourly(JULY - timedelta(days=10), 40, 8.0))["themes"]["warmth"]
        self.assertEqual(cool["score"], 0)

    def test_humidity_and_air_bands(self):
        self.assertEqual([review.humidity_category(v) for v in (45, 55, 65, 75, 22)], [1, 2, 3, 4, 3])
        self.assertEqual([review.air_category(v) for v in (900, 1150, 1700, 1800)], [1, 2, 3, 4])

    def test_letters(self):
        self.assertEqual([review.letter(s) for s in (100, 85, 84.6, 70, 55, 40, 39, None)], ["A", "A", "A", "B", "C", "D", "E", None])


class Rooms(unittest.TestCase):
    def test_a_room_is_graded_on_what_it_measures(self):
        outdoor = hourly(JANUARY, 30, 6.0)
        salon = review.room({"temperature": hourly(JANUARY, 30, 21.5), "humidity": hourly(JANUARY, 30, 45),
                             "co2": hourly(JANUARY, 30, 700)}, outdoor)
        self.assertEqual(set(salon["themes"]), {"warmth", "humidity", "air"})
        self.assertEqual((salon["score"], salon["letter"]), (100, "A"))
        bedroom = review.room({"temperature": hourly(JANUARY, 30, 19.0), "humidity": hourly(JANUARY, 30, 55)}, outdoor)
        self.assertEqual(set(bedroom["themes"]), {"warmth", "humidity"})
        self.assertEqual(bedroom["score"], round((50 + 75) / 2))

    def test_an_unheated_room_is_not_graded_on_its_warmth(self):
        laundry = review.room({"temperature": hourly(JANUARY, 30, 14.0), "humidity": hourly(JANUARY, 30, 55)}, hourly(JANUARY, 30, 6.0), heated=False)
        self.assertEqual(set(laundry["themes"]), {"humidity"})
        self.assertEqual(laundry["letter"], "B")

    def test_two_weeks_of_measures_before_a_grade(self):
        young = review.room({"humidity": hourly(JANUARY, 10, 45)}, [])
        self.assertIsNone(young["themes"]["humidity"]["score"])
        self.assertIsNone(young["letter"])

    def test_the_home_is_the_mean_of_its_rooms(self):
        outdoor = hourly(JANUARY, 30, 6.0)
        rooms = [review.room({"temperature": hourly(JANUARY, 30, 21.5), "co2": hourly(JANUARY, 30, 700)}, outdoor),
                 review.room({"temperature": hourly(JANUARY, 30, 19.0)}, outdoor)]
        home = review.home(rooms)
        self.assertEqual(home["score"], round((100 + 50) / 2))
        self.assertEqual(home["themes"]["warmth"], {"score": 75, "letter": "B", "rooms": 2})
        # Only the rooms with a CO₂ sensor speak for the air.
        self.assertEqual(home["themes"]["air"]["rooms"], 1)
        self.assertIsNone(home["themes"]["humidity"]["score"])

    def test_hours_are_read_in_the_home_time_zone(self):
        """23 h UTC on 31 December is already January in Paris: the month and the typical day follow local time."""
        points = hourly(datetime(2025, 12, 31, 23, tzinfo=timezone.utc), 20, 20.5)
        warm = review.room({"temperature": points}, hourly(JANUARY, 30, 6.0), PARIS)["themes"]["warmth"]
        self.assertEqual(warm["monthly"][0]["month"], "2026-01")
        self.assertEqual(warm["day"]["winter"][0], 20.5)


class Advice(unittest.TestCase):
    """Advice only for a lasting problem the measures show; never « heat more » to a home kept at the legal 19 °C."""
    def test_a_room_out_of_every_category_is_told_to_heat(self):
        outdoor = hourly(JANUARY, 30, 6.0)
        legal = review.room({"temperature": hourly(JANUARY, 30, 19.0)}, outdoor)
        self.assertEqual(review.advice(legal), [])
        cold = review.room({"temperature": hourly(JANUARY, 30, lambda t: 17.0 if t.hour < 8 else 19.5)}, outdoor)
        self.assertEqual([(a["key"], a["share"]) for a in review.advice(cold)], [("heat_more", 33)])

    def test_a_damp_room_runs_its_ventilation_or_is_aired(self):
        damp = review.room({"humidity": hourly(JANUARY, 30, lambda t: 75 if t.hour < 6 else 55)}, [])
        self.assertEqual(review.advice(damp)[0]["key"], "air_daily")
        self.assertEqual(review.advice(damp, ventilation=True)[0]["key"], "run_ventilation")
        # 65 %, above the standard's normal range but under Confort's mould threshold: nothing to do.
        self.assertEqual(review.advice(review.room({"humidity": hourly(JANUARY, 30, 65)}, [])), [])

    def test_stale_air_names_its_worst_hour(self):
        stale = review.room({"co2": hourly(JANUARY, 30, lambda t: 1900 if t.hour in (21, 22) else 600)}, [])
        self.assertEqual([(a["key"], a["hour"]) for a in review.advice(stale)], [("air_at", 21)])

    def test_the_house_is_told_to_open_at_night_after_a_warm_summer(self):
        dawn_cool = lambda t: 18.0 if 3 <= t.hour <= 7 else 30.0
        warm = review.room({"temperature": hourly(JULY, 40, 27.0)}, hourly(JULY - timedelta(days=10), 50, dawn_cool))
        found = review.home_advice([{"title": "Salon", **warm, "advice": []}])
        self.assertEqual([a["key"] for a in found], ["open_at_night", "add_co2"])
        self.assertEqual(found[0]["gap"], 9.0)
        mild = review.room({"temperature": hourly(JULY, 40, 23.0)}, hourly(JULY - timedelta(days=10), 50, dawn_cool))
        self.assertNotIn("open_at_night", [a["key"] for a in review.home_advice([{"title": "Salon", **mild, "advice": []}])])

    def test_the_rooms_advice_comes_first_with_their_name(self):
        outdoor = hourly(JANUARY, 30, 6.0)
        cold = review.room({"temperature": hourly(JANUARY, 30, 16.0), "co2": hourly(JANUARY, 30, 600)}, outdoor)
        found = review.home_advice([{"title": "Chambre P", "entry_id": "p", **cold, "advice": review.advice(cold)}])
        self.assertEqual((found[0]["key"], found[0]["room"], found[0]["entry_id"]), ("heat_more", "Chambre P", "p"))
        self.assertNotIn("add_co2", [a["key"] for a in found])


class Source(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from homeassistant.core import HomeAssistant
        from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()

        class Coordinator:
            def __init__(self, config):
                self.config = config

            def _outdoor_entity(self):
                return "sensor.outdoor"

        for title, config in (("Salon", {"sources": {"indoor_temperature": "sensor.t_salon", "co2": "sensor.co2"}}),
                              ("Buanderie", {"heated": False, "sources": {"indoor_temperature": "sensor.t_b", "indoor_humidity": "sensor.h_b"}})):
            entry = ConfigEntry(domain="niak_comfort", title=title, unique_id=title, version=1, minor_version=1, source="user",
                                data={"name": title}, options={}, discovery_keys={}, subentries_data=[])
            entry.runtime_data = Coordinator(config)
            self.hass.config_entries._entries[entry.entry_id] = entry
            entry._async_set_state(self.hass, ConfigEntryState.LOADED, None)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    async def test_the_review_reads_a_year_of_statistics_once_an_hour(self):
        from custom_components.niak_comfort import review_source
        rows = lambda value: [{"start": (JANUARY + timedelta(hours=h)).timestamp(), "mean": value} for h in range(30 * 24)]
        stats = {"sensor.t_salon": rows(21.5), "sensor.co2": rows(700), "sensor.t_b": rows(14.0), "sensor.h_b": rows(55), "sensor.outdoor": rows(6.0)}
        calls = []

        async def statistics(hass, ids, start, end):
            calls.append(set(ids))
            return {i: stats[i] for i in ids}

        now = JANUARY + timedelta(days=40)
        with patch.object(review_source, "_statistics", statistics):
            first = await review_source.async_review(self.hass, now)
            again = await review_source.async_review(self.hass, now + timedelta(minutes=30))
        self.assertEqual(calls, [{"sensor.t_salon", "sensor.co2", "sensor.t_b", "sensor.h_b", "sensor.outdoor"}])
        self.assertIs(first, again)
        rooms = {r["title"]: r for r in first["rooms"]}
        self.assertEqual(rooms["Salon"]["letter"], "A")
        self.assertEqual(set(rooms["Buanderie"]["themes"]), {"humidity"})
        self.assertEqual(first["home"]["score"], round((100 + 75) / 2))


class Periods(unittest.TestCase):
    """The home card's day, week and month: the review's themes over a short window, each room's range."""

    def rooms(self, now):
        start = now - timedelta(days=30)
        salon = {"entry_id": "s", "title": "Salon", "heated": True,
                 "series": {"temperature": hourly(start, 30, lambda t: 21.0 if t.hour >= 8 else 19.0),
                            "humidity": hourly(start, 30, 65.0), "co2": hourly(start, 30, 700.0)}}
        laundry = {"entry_id": "b", "title": "Buanderie", "heated": False,
                   "series": {"temperature": hourly(start, 30, 17.5)}}
        return [salon, laundry]

    def test_a_day_is_graded_on_its_own_hours(self):
        now = JANUARY + timedelta(days=40)
        day = review.period(self.rooms(now), hourly(JANUARY, 40, 6.0), now, "day")
        salon, laundry = day["rooms"]
        self.assertEqual((salon["min"], salon["max"]), (19.0, 21.0))
        self.assertIsNotNone(day["themes"]["warmth"]["letter"])
        self.assertEqual(day["themes"]["humidity"]["share"], 100)
        self.assertIsNotNone(day["themes"]["comfort"]["score"])
        # An unheated room shows its range but is not graded on its warmth.
        self.assertEqual(laundry["min"], 17.5)
        self.assertNotIn("warmth", laundry["themes"])
        self.assertEqual(len(day["curve"]["inside"]), 24)
        self.assertEqual(day["outdoor"]["mean"], 6.0)

    def test_the_month_steps_by_six_hours_and_needs_ten_days(self):
        now = JANUARY + timedelta(days=40)
        month = review.period(self.rooms(now), hourly(JANUARY, 40, 6.0), now, "month")
        self.assertEqual((month["step_hours"], len(month["curve"]["inside"])), (6, 120))
        short = [{**r, "series": {k: v[-5 * 24:] for k, v in r["series"].items()}} for r in self.rooms(now)]
        self.assertIsNone(review.period(short, [], now, "month")["themes"]["warmth"]["score"])


if __name__ == "__main__":
    unittest.main()
