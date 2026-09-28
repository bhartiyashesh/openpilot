"""
Facts for the mode question, and the question itself. Code computes facts only; Jev decides.
Same design as the offline evaluation (typesafe-drive tools/switcher.py).
"""
from dataclasses import dataclass

QUESTION = "mode"
MODE = {
  "acc": "Plain adaptive cruise: holds the set speed and follows the car ahead. Smooth, but never stops for a red light "
         + "or stop sign and does not slow for turns by itself.",
  "blended": "End-to-end (experimental) longitudinal: the camera model also stops for red lights and stop signs and slows "
             + "for turns. Less smooth on open road.",
}
RULES = {
  "question": "Which longitudinal mode should openpilot use right now?",
  "controls": "Use blended from about 8 s (at least 150 m) before a traffic light or stop sign (traffic_control) until the "
              + "car has passed it or stopped and pulled away.",
  "vision": "Use blended whenever vision.should_stop is true, or the lead car is stopped or much slower in city traffic "
            + "(stop and go).",
  "turns": "Use blended when a turn sharper than 45 degrees is within 150 m.",
  "open_road": "Otherwise use acc (open road, highway cruising).",
  "stability": "Avoid flapping: once switched, keep a mode for at least 5 s (current.seconds_in_mode) unless a control or "
               + "should_stop appears.",
}


@dataclass
class Memory:
  """What the facts need from the past: time stopped, current mode and since when."""
  stopped_since: float | None = None
  mode: str = "acc"
  mode_since: float = 0.0

  def update_motion(self, now: float, speed_ms: float) -> None:
    self.stopped_since = (self.stopped_since if self.stopped_since is not None else now) if speed_ms < 0.3 else None

  def set_mode(self, now: float, mode: str) -> None:
    if mode != self.mode:
      self.mode, self.mode_since = mode, now


def build_state(now: float, speed_ms: float, control: dict, turn: dict | None, should_stop: bool, desired_accel: float,
                lead: dict, memory: Memory, source: str) -> dict:
  speed_kmh = speed_ms * 3.6
  control = dict(control)
  if control.get("present"):
    control["seconds_away"] = round(control["distance_m"] / max(speed_ms, 0.5), 1)
  return {
    "objective": "You choose openpilot's longitudinal mode. openpilot drives; you decide when it needs its end-to-end mode.",
    "speed_kmh": round(speed_kmh, 1),
    "traffic_control": control,
    "map_source": source,
    "next_turn": turn,
    "vision": {"should_stop": bool(should_stop), "desired_accel_ms2": round(float(desired_accel), 2)},
    "lead": lead,
    "stopped_for_s": round(now - memory.stopped_since) if memory.stopped_since is not None else 0,
    "current": {"mode": memory.mode, "seconds_in_mode": round(now - memory.mode_since)},
  }


MAP_RULE_M, MAP_RULE_S = 150.0, 8.0  # a light / stop sign this close (distance or time) needs end-to-end
SHARP_TURN_DEG, SHARP_TURN_M = 45.0, 150.0


def map_rule_blended(control: dict, turn: dict | None, speed_ms: float) -> bool:
  """Network-free rule that runs on the car even without Jev: end-to-end near mapped controls and sharp turns."""
  if control.get("present") and control["distance_m"] <= max(MAP_RULE_M, MAP_RULE_S * speed_ms):
    return True
  return bool(turn and turn.get("angle_deg") is not None and abs(turn["angle_deg"]) > SHARP_TURN_DEG
              and 0 < turn["distance_m"] <= SHARP_TURN_M)


def questions() -> dict:
  return {QUESTION: {"type": "choice", "instructions": RULES, "criteria": MODE}}
