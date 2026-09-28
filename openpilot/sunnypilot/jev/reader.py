"""
Hand-off between jevd and the longitudinal planner through a small file in RAM. The planner
side never raises and treats anything missing, malformed or stale as "no Jev opinion".
"""
import json
import os
import time
from pathlib import Path

MODE_PATH = Path("/dev/shm/jev_mode.json")
MAX_AGE_S = 2.5  # older decisions are ignored (Jev slow or offline -> DEC alone)
READ_EVERY_S = 0.25


def write_mode(mode: str, path: Path = MODE_PATH, now: float | None = None) -> None:
  """Atomically publish a decision stamped with the monotonic clock (shared by processes)."""
  tmp = path.with_suffix(".tmp")
  tmp.write_text(json.dumps({"mode": mode, "t": time.monotonic() if now is None else now}))
  os.replace(tmp, path)


class JevModeReader:
  def __init__(self, path: Path = MODE_PATH, clock=time.monotonic):
    self._path = path
    self._clock = clock
    self._last_read = -1e9
    self._mode: str | None = None
    self._t = -1e9

  def wants_blended(self) -> bool:
    now = self._clock()
    if now - self._last_read >= READ_EVERY_S:
      self._last_read = now
      try:
        data = json.loads(self._path.read_text())
        self._mode, self._t = str(data["mode"]), float(data["t"])
      except (OSError, ValueError, KeyError, TypeError):
        self._mode, self._t = None, -1e9
    return self._mode == "blended" and now - self._t < MAX_AGE_S
