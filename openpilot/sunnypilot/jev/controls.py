"""
Where the traffic lights and stop signs ahead are.

With a navigation destination (NavDestination, set from comma connect) and a Mapbox token:
the Mapbox route, its traffic_signal / stop_sign intersections and its turns, all measured
along the route. Without one: OpenStreetMap signals and stop signs near the car, keeping those
ahead of the current heading. Network calls happen in refresh(); ahead() is pure and cheap.
"""
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

import requests

from openpilot.sunnypilot.jev.geo import angle_diff, bearing_deg, distance_m, local_xy

# Public Overpass servers are shared and often busy: try mirrors, then back off.
OVERPASS_URLS = (
  "https://overpass-api.de/api/interpreter",
  "https://overpass.kumi.systems/api/interpreter",
  "https://overpass.private.coffee/api/interpreter",
)
OSM_RETRY_AFTER_S = 60.0
USER_AGENT = "sunnypilot-jev/1.0 (+https://github.com/bhartiyashesh/sunnypilot)"  # Overpass rejects anonymous clients (406)
OSM_RADIUS_M = 2000.0
OSM_REFRESH_MOVED_M = 1000.0  # re-query after moving this far from the last query point
OSM_MAX_AGE_S = 300.0
AHEAD_MAX_M = 250.0
AHEAD_CONE_DEG = 25.0  # a node counts as ahead if it is within this angle of our heading
AHEAD_LATERAL_M = 25.0  # and this close to the line we are driving along

DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving/{lon0},{lat0};{lon1},{lat1}"
ROUTE_OFF_M = 60.0  # farther than this from the route -> re-route
ROUTE_REFRESH_MIN_S = 30.0
CONTROL_MERGE_M = 15.0
HTTP_TIMEOUT_S = 10.0


class OsmControls:
  def __init__(self, session):
    self._session = session
    self.nodes: list[dict] = []
    self._center: tuple[float, float] | None = None
    self._fetched_at = -1e9
    self._retry_at = -1e9

  def needs_refresh(self, lat: float, lon: float, now: float) -> bool:
    if now < self._retry_at:
      return False
    if self._center is None or now - self._fetched_at > OSM_MAX_AGE_S:
      return True
    return distance_m(self._center[0], self._center[1], lat, lon) > OSM_REFRESH_MOVED_M

  def refresh(self, lat: float, lon: float, now: float) -> None:
    query = (f'[out:json][timeout:10];node(around:{OSM_RADIUS_M:.0f},{lat:.6f},{lon:.6f})'
             + '["highway"~"^(traffic_signals|stop)$"];out;')
    error: Exception | None = None
    for url in OVERPASS_URLS:
      try:
        response = self._session.post(url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT_S)
        response.raise_for_status()
        break
      except requests.RequestException as e:
        error = e
    else:
      self._retry_at = now + OSM_RETRY_AFTER_S  # all servers failed: keep the old nodes, try later
      assert error is not None
      raise error
    self.nodes = [
      {"lat": e["lat"], "lon": e["lon"], "type": "traffic_light" if e["tags"]["highway"] == "traffic_signals" else "stop_sign"}
      for e in response.json().get("elements", []) if "lat" in e and "tags" in e
    ]
    self._center, self._fetched_at = (lat, lon), now

  def ahead(self, lat: float, lon: float, heading: float) -> dict:
    return pick_ahead(self.nodes, lat, lon, heading)


def pick_ahead(nodes, lat: float, lon: float, heading: float) -> dict:
  """Nearest traffic light / stop sign ahead of the heading, within AHEAD_MAX_M."""
  best = None
  for node in nodes:
    d = distance_m(lat, lon, node["lat"], node["lon"])
    off = angle_diff(bearing_deg(lat, lon, node["lat"], node["lon"]), heading)
    if 0 < d <= AHEAD_MAX_M and abs(off) <= AHEAD_CONE_DEG and d * abs(math.sin(math.radians(off))) <= AHEAD_LATERAL_M:
      if best is None or d < best[0]:
        best = (d, node["type"])
  return {"present": True, "type": best[1], "distance_m": round(best[0])} if best else {"present": False}


# Prebuilt OpenStreetMap extract (data (c) OpenStreetMap contributors, ODbL): no network needed.
OFFLINE_PATHS = (Path("/data/jev/osm_controls.json.gz"), Path(__file__).parent / "data" / "illinois_controls.json.gz")
GRID_DEG = 0.01  # ~1.1 km north-south; neighbouring cells cover AHEAD_MAX_M
TYPES = ("traffic_light", "stop_sign")


class OfflineControls:
  def __init__(self, nodes: list[list[int]]):
    self._grid: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for lat5, lon5, kind in nodes:
      lat, lon = lat5 / 1e5, lon5 / 1e5
      self._grid[(int(lat // GRID_DEG), int(lon // GRID_DEG))].append({"lat": lat, "lon": lon, "type": TYPES[kind]})

  @classmethod
  def load(cls, paths=OFFLINE_PATHS) -> "OfflineControls | None":
    for path in paths:
      try:
        with gzip.open(path, "rt") as f:
          return cls(json.load(f)["nodes"])
      except (OSError, ValueError, KeyError):
        continue
    return None

  def ahead(self, lat: float, lon: float, heading: float) -> dict:
    row, col = int(lat // GRID_DEG), int(lon // GRID_DEG)
    nearby = [n for dr in (-1, 0, 1) for dc in (-1, 0, 1) for n in self._grid.get((row + dr, col + dc), ())]
    return pick_ahead(nearby, lat, lon, heading)


class MapboxRoute:
  def __init__(self, session, token: str):
    self._session = session
    self._token = token
    self.destination: tuple[float, float] | None = None
    self.points: list[tuple[float, float]] = []  # (lat, lon)
    self.s: list[float] = []
    self.controls: list[dict] = []
    self.turns: list[dict] = []
    self._fetched_at = -1e9

  def set_destination(self, destination: tuple[float, float] | None) -> None:
    if destination != self.destination:
      self.destination = destination
      self.points, self.s, self.controls, self.turns = [], [], [], []

  def needs_refresh(self, lat: float, lon: float, now: float) -> bool:
    if self.destination is None or now - self._fetched_at < ROUTE_REFRESH_MIN_S:
      return False
    return not self.points or self.locate(lat, lon)[1] > ROUTE_OFF_M

  def refresh(self, lat: float, lon: float, heading: float, now: float) -> None:
    assert self.destination is not None
    self._fetched_at = now
    url = DIRECTIONS_URL.format(lat0=lat, lon0=lon, lat1=self.destination[0], lon1=self.destination[1])
    params = {"steps": "true", "geometries": "geojson", "overview": "full", "bearings": f"{heading:.0f},45;", "access_token": self._token}
    response = self._session.get(url, params=params, timeout=HTTP_TIMEOUT_S)
    response.raise_for_status()
    routes = response.json().get("routes") or []
    if routes:
      self.load(routes[0])

  def load(self, route: dict) -> None:
    """Build the polyline, turns and controls from one Mapbox route (Directions or Matching)."""
    self.points, self.s, self.turns, self.controls = [], [], [], []
    steps = [step for leg in route["legs"] for step in leg["steps"]]
    for step in steps:
      for lon, lat in step["geometry"]["coordinates"]:
        if self.points and (lat, lon) == self.points[-1]:
          continue
        self.s.append(self.s[-1] + distance_m(*self.points[-1], lat, lon) if self.points else 0.0)
        self.points.append((lat, lon))
    for step in steps:
      maneuver = step["maneuver"]
      if maneuver.get("type") not in ("depart", "arrive"):
        angle = angle_diff(maneuver.get("bearing_after", 0.0), maneuver.get("bearing_before", 0.0))
        lon, lat = maneuver.get("location") or step["geometry"]["coordinates"][0]
        self.turns.append({"s": self.locate(lat, lon)[0], "angle_deg": round(angle), "type": maneuver.get("type")})
    for step in steps:
      for intersection in step.get("intersections", []):
        kind = "stop_sign" if intersection.get("stop_sign") else "traffic_light" if intersection.get("traffic_signal") else None
        if kind:
          lon, lat = intersection["location"]
          s, _ = self.locate(lat, lon)
          if not any(abs(c["s"] - s) < CONTROL_MERGE_M for c in self.controls):
            self.controls.append({"s": s, "type": kind})
    self.controls.sort(key=lambda c: c["s"])

  def locate(self, lat: float, lon: float) -> tuple[float, float]:
    """(distance along the route, meters off it), projecting onto segments."""
    best = (math.inf, 0.0)
    for i in range(len(self.points) - 1):
      (lat_a, lon_a), (lat_b, lon_b) = self.points[i], self.points[i + 1]
      bx, by = local_xy(lat_a, lon_a, lat_b, lon_b)
      px, py = local_xy(lat_a, lon_a, lat, lon)
      length2 = bx * bx + by * by
      f = min(max((px * bx + py * by) / length2, 0.0), 1.0) if length2 > 0 else 0.0
      d = math.hypot(px - f * bx, py - f * by)
      if d < best[0]:
        best = (d, self.s[i] + f * (self.s[i + 1] - self.s[i]))
    return best[1], best[0]

  def ahead(self, lat: float, lon: float) -> tuple[dict, dict | None]:
    s, off = self.locate(lat, lon)
    if off > ROUTE_OFF_M:
      return {"present": False}, None
    control = next((c for c in self.controls if -5 < c["s"] - s <= AHEAD_MAX_M), None)
    turn = next((t for t in self.turns if t["s"] > s + 5), None)
    control_out = {"present": True, "type": control["type"], "distance_m": round(control["s"] - s)} if control else {"present": False}
    turn_out = {"angle_deg": turn["angle_deg"], "distance_m": round(turn["s"] - s), "type": turn["type"]} if turn else None
    return control_out, turn_out
