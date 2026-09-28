import json

import pytest

from openpilot.sunnypilot.jev import client, config, logic
from openpilot.sunnypilot.jev.controls import MapboxRoute, OsmControls
from openpilot.sunnypilot.jev.geo import compass_point, distance_m
from openpilot.sunnypilot.jev.reader import JevModeReader, write_mode

LAT, LON = 42.0, -87.8
M_LAT = 1 / 111195.0  # degrees of latitude per meter


class TestCompass:
  @pytest.mark.parametrize("bearing,point", [
    (0, "N"), (22, "N"), (23, "NE"), (45, "NE"), (90, "E"), (135, "SE"), (180, "S"),
    (225, "SW"), (270, "W"), (315, "NW"), (337, "NW"), (338, "N"), (359.9, "N"), (-90, "W"), (720, "N"),
  ])
  def test_eight_points(self, bearing, point):
    assert compass_point(bearing) == point


class TestReader:
  def test_fresh_blended_counts_stale_and_broken_do_not(self, tmp_path):
    path, clock = tmp_path / "mode.json", [100.0]
    reader = JevModeReader(path, clock=lambda: clock[0])
    assert not reader.wants_blended()  # no file
    write_mode("blended", path, now=100.0)
    clock[0] = 101.0
    assert reader.wants_blended()
    clock[0] = 103.0  # 3 s old: Jev silent -> DEC alone
    assert not reader.wants_blended()
    write_mode("acc", path, now=103.0)
    clock[0] = 103.5
    assert not reader.wants_blended()
    path.write_text("{not json")
    clock[0] = 104.0
    assert not reader.wants_blended()


class TestConfig:
  def test_needs_enabled_and_key(self, tmp_path):
    path = tmp_path / "config.json"
    assert not config.enabled(path)
    path.write_text(json.dumps({"enabled": True}))
    assert not config.enabled(path)
    path.write_text(json.dumps({"enabled": True, "typesafe_api_key": "k"}))
    assert config.enabled(path)


class TestOsm:
  def test_picks_nearest_node_ahead_of_heading(self):
    osm = OsmControls(session=None)
    osm.nodes = [
      {"lat": LAT + 120 * M_LAT, "lon": LON, "type": "traffic_light"},  # 120 m north
      {"lat": LAT + 60 * M_LAT, "lon": LON + 0.002, "type": "stop_sign"},  # ~165 m to the side
      {"lat": LAT - 50 * M_LAT, "lon": LON, "type": "stop_sign"},  # behind
    ]
    ahead = osm.ahead(LAT, LON, heading=0.0)
    assert ahead["present"] and ahead["type"] == "traffic_light" and 115 <= ahead["distance_m"] <= 125
    assert not osm.ahead(LAT, LON, heading=90.0)["present"]  # driving east: nothing ahead

  def test_refresh_parses_overpass(self):
    class Response:
      def raise_for_status(self):
        pass

      def json(self):
        return {"elements": [{"lat": LAT, "lon": LON, "tags": {"highway": "traffic_signals"}},
                             {"lat": LAT, "lon": LON, "tags": {"highway": "stop"}}]}

    class Session:
      def post(self, url, data, headers, timeout):
        assert "traffic_signals|stop" in data["data"] and headers["User-Agent"].startswith("sunnypilot-jev")
        return Response()

    osm = OsmControls(Session())
    assert osm.needs_refresh(LAT, LON, now=0.0)
    osm.refresh(LAT, LON, now=0.0)
    assert [n["type"] for n in osm.nodes] == ["traffic_light", "stop_sign"]
    assert not osm.needs_refresh(LAT + 100 * M_LAT, LON, now=10.0)
    assert osm.needs_refresh(LAT + 1200 * M_LAT, LON, now=10.0)


def _straight_route():
  """1 km north, a traffic light at 400 m, a right turn (+90) at the end."""
  coords = [[LON, LAT + i * 100 * M_LAT] for i in range(11)]
  light = {"location": [LON, LAT + 400 * M_LAT], "traffic_signal": True}
  return {"legs": [{"steps": [
    {"geometry": {"coordinates": coords}, "maneuver": {"type": "depart", "bearing_before": 0, "bearing_after": 0},
     "intersections": [light]},
    {"geometry": {"coordinates": [coords[-1], [LON + 0.001, coords[-1][1]]]},
     "maneuver": {"type": "turn", "bearing_before": 0, "bearing_after": 90}, "intersections": []},
  ]}]}


class TestMapbox:
  def test_route_controls_and_turns_ahead(self):
    route = MapboxRoute(session=None, token="t")
    route.load(_straight_route())
    assert [c["type"] for c in route.controls] == ["traffic_light"]
    control, turn = route.ahead(LAT + 250 * M_LAT, LON)
    assert control["present"] and 145 <= control["distance_m"] <= 155
    assert turn["angle_deg"] == 90 and 745 <= turn["distance_m"] <= 755
    control, _ = route.ahead(LAT + 900 * M_LAT, LON)  # past the light
    assert not control["present"]
    off_route, _ = route.ahead(LAT + 250 * M_LAT, LON + 0.01)  # ~800 m east of the route
    assert not off_route["present"]

  def test_locate_projects_onto_segments(self):
    route = MapboxRoute(session=None, token="t")
    route.load(_straight_route())
    s, off = route.locate(LAT + 250 * M_LAT, LON + 0.0001)
    assert abs(s - 250) < 2 and abs(off - distance_m(LAT, LON, LAT, LON + 0.0001)) < 1


class TestClient:
  class Session:
    def __init__(self, payload=None, error=None):
      self.payload, self.error, self.sent = payload, error, None

    def post(self, url, json, headers, timeout):
      if self.error:
        raise self.error
      self.sent = (url, json, headers)
      payload = self.payload

      class Response:
        def raise_for_status(self):
          pass

        def json(self):
          return payload
      return Response()

  def test_sends_system_one_payload_and_reads_choice(self):
    session = self.Session({"answers": {"mode": {"type": "choice", "choice": "blended", "probabilities": {}}}})
    assert client.ask(session, "key", {"speed_kmh": 1}, logic.questions(), "mode") == "blended"
    url, body, headers = session.sent
    assert url.endswith("/v1/systemone") and headers["Authorization"] == "Bearer key"
    assert body["model"] == "jev-latest" and body["questions"]["mode"]["type"] == "choice"

  @pytest.mark.parametrize("session", [Session(error=TimeoutError()), Session(payload={"answers": {}}), Session(payload=[])])
  def test_any_failure_is_no_opinion(self, session):
    assert client.ask(session, "key", {}, logic.questions(), "mode") is None


class TestLogic:
  def test_facts_and_memory(self):
    memory = logic.Memory()
    memory.update_motion(10.0, 0.0)
    memory.set_mode(10.0, "blended")
    state = logic.build_state(15.0, 10.0, {"present": True, "type": "stop_sign", "distance_m": 50}, None, True, -1.2,
                              {"present": False}, memory, "osm")
    assert state["traffic_control"]["seconds_away"] == 5.0
    assert state["current"] == {"mode": "blended", "seconds_in_mode": 5}
    assert state["stopped_for_s"] == 5 and state["vision"]["should_stop"] is True
    memory.update_motion(16.0, 5.0)
    assert memory.stopped_since is None


def test_osm_tries_mirrors_then_backs_off():
  import requests

  class Session:
    def __init__(self):
      self.urls = []

    def post(self, url, data, headers, timeout):
      self.urls.append(url)
      raise requests.ConnectionError("busy")

  session = Session()
  osm = OsmControls(session)
  with pytest.raises(requests.ConnectionError):
    osm.refresh(LAT, LON, now=0.0)
  assert len(session.urls) == 3  # every mirror tried once
  assert not osm.needs_refresh(LAT, LON, now=30.0)  # backing off
  assert osm.needs_refresh(LAT, LON, now=61.0)
