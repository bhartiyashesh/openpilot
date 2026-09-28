#!/usr/bin/env python3
"""
jevd: once a second, ask Jev whether openpilot should drive end-to-end ("blended") and publish
the answer for the longitudinal planner (see reader.py). The planner only ever ADDS end-to-end
time on top of Dynamic Experimental Control, and ignores answers older than 2.5 s.

Map facts: Mapbox route when /data/jev/destination.json and a mapbox_token exist, otherwise
OpenStreetMap. Map lookups run in their own thread so a slow network never delays a decision.
Every decision is appended to /data/jev/log/ for later review.
"""
import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

import openpilot.cereal.messaging as messaging
from openpilot.common.realtime import Ratekeeper
from openpilot.common.swaglog import cloudlog
from openpilot.sunnypilot.jev import client, config, logic
from openpilot.sunnypilot.jev.controls import MapboxRoute, OsmControls
from openpilot.sunnypilot.jev.reader import write_mode

DESTINATION_PATH = Path("/data/jev/destination.json")
LOG_DIR = Path("/data/jev/log")
LOG_MAX_BYTES = 20 * 1024 * 1024
CONFIG_EVERY_S = 10.0


def read_destination(path: Path = DESTINATION_PATH) -> tuple[float, float] | None:
  try:
    data = json.loads(path.read_text())
    return float(data["lat"]), float(data["lon"])
  except (OSError, ValueError, KeyError, TypeError):
    return None


class MapWorker(threading.Thread):
  """Keeps the map facts fresh for the latest position without blocking the decision loop."""

  def __init__(self, session: requests.Session, mapbox_token: str | None):
    super().__init__(daemon=True)
    self.osm = OsmControls(session)
    self.route = MapboxRoute(session, mapbox_token) if mapbox_token else None
    self.position: tuple[float, float, float] | None = None  # lat, lon, heading

  def run(self) -> None:
    while True:
      position = self.position
      if position is not None:
        lat, lon, heading = position
        now = time.monotonic()
        try:
          if self.route is not None:
            self.route.set_destination(read_destination())
            if self.route.needs_refresh(lat, lon, now):
              self.route.refresh(lat, lon, heading, now)
          if self.osm.needs_refresh(lat, lon, now):
            self.osm.refresh(lat, lon, now)
        except requests.RequestException as e:
          cloudlog.warning(f"jevd: map refresh failed: {e}")
      time.sleep(2.0)

  def ahead(self, lat: float, lon: float, heading: float) -> tuple[dict, dict | None, str]:
    if self.route is not None and self.route.points:
      control, turn = self.route.ahead(lat, lon)
      return control, turn, "mapbox"
    return self.osm.ahead(lat, lon, heading), None, "osm"


def open_log():
  LOG_DIR.mkdir(parents=True, exist_ok=True)
  return (LOG_DIR / f"jev-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.jsonl").open("a")


def main() -> None:
  cfg = config.load()
  session = requests.Session()
  worker = MapWorker(session, cfg.get("mapbox_token"))
  worker.start()
  sm = messaging.SubMaster(["carState", "modelV2", "radarState", "gpsLocationExternal", "gpsLocation"])
  memory = logic.Memory()
  questions = logic.questions()
  rk = Ratekeeper(1.0, print_delay_threshold=None)
  log = open_log()
  last_config = time.monotonic()

  while True:
    sm.update(0)
    now = time.monotonic()
    if now - last_config > CONFIG_EVERY_S:
      cfg, last_config = config.load(), now
    gps = next((sm[s] for s in ("gpsLocationExternal", "gpsLocation") if sm.alive[s] and sm[s].hasFix), None)
    if not cfg.get("enabled") or not cfg.get("typesafe_api_key") or gps is None:
      rk.keep_time()
      continue

    speed = sm["carState"].vEgo
    memory.update_motion(now, speed)
    worker.position = (gps.latitude, gps.longitude, gps.bearingDeg)
    control, turn, source = worker.ahead(gps.latitude, gps.longitude, gps.bearingDeg)
    lead_msg = sm["radarState"].leadOne
    lead = {"present": bool(lead_msg.present), "gap_m": round(lead_msg.dRel, 1) if lead_msg.present else None,
            "speed_kmh": round(lead_msg.vLead * 3.6, 1) if lead_msg.present else None}
    action = sm["modelV2"].action
    state = logic.build_state(now, speed, control, turn, action.shouldStop, action.desiredAcceleration, lead, memory, source)

    started = time.monotonic()
    mode = client.ask(session, cfg["typesafe_api_key"], state, questions, logic.QUESTION)
    latency_ms = round((time.monotonic() - started) * 1000)
    if mode in logic.MODE:
      memory.set_mode(now, mode)
      write_mode(mode)

    log.write(json.dumps({"t": round(now, 1), "mode": mode, "latency_ms": latency_ms, "state": state}) + "\n")
    log.flush()
    if log.tell() > LOG_MAX_BYTES:
      log.close()
      log = open_log()
    rk.keep_time()


if __name__ == "__main__":
  main()
