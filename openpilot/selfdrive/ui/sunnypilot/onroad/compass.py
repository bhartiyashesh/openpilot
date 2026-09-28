"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import pyray as rl

from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.sunnypilot.jev.geo import compass_point
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget

GPS_SERVICES = ("gpsLocationExternal", "gpsLocation")
MIN_SPEED_MS = 1.0  # GPS course is noise when nearly stopped: keep the last heading
MARGIN = 12  # mici screen is 536x240
TEXT_SIZE = 34


class CompassRenderer(Widget):
  """Direction of travel as text (N, NE, E, SE, S, SW, W, NW), from GPS course."""

  def __init__(self):
    super().__init__()
    self.bearing: float | None = None
    self._font = gui_app.font(FontWeight.BOLD)

  def update(self) -> None:
    sm = ui_state.sm
    for service in GPS_SERVICES:
      if service not in sm.services or not sm.updated[service]:
        continue
      gps = sm[service]
      if gps.hasFix and gps.speed > MIN_SPEED_MS:
        self.bearing = gps.bearingDeg % 360.0
        return

  def _render(self, rect: rl.Rectangle) -> None:
    if self.bearing is None:
      return
    direction = compass_point(self.bearing)
    size = measure_text_cached(self._font, direction, TEXT_SIZE)
    pos = rl.Vector2(rect.x + rect.width - size.x - MARGIN, rect.y + MARGIN)
    rl.draw_text_ex(self._font, direction, pos, TEXT_SIZE, 0, rl.Color(255, 255, 255, 230))
