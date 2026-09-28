import math

EARTH_RADIUS_M = 6371000.0
COMPASS_POINTS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def local_xy(lat0: float, lon0: float, lat: float, lon: float) -> tuple[float, float]:
  """Meters east / north of (lat0, lon0); fine within a few km."""
  x = math.radians(lon - lon0) * math.cos(math.radians(lat0)) * EARTH_RADIUS_M
  y = math.radians(lat - lat0) * EARTH_RADIUS_M
  return x, y


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
  return math.hypot(*local_xy(lat1, lon1, lat2, lon2))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
  """Bearing from point 1 to point 2, degrees clockwise from north."""
  x, y = local_xy(lat1, lon1, lat2, lon2)
  return math.degrees(math.atan2(x, y)) % 360.0


def angle_diff(a: float, b: float) -> float:
  """Signed a - b wrapped to [-180, 180)."""
  return (a - b + 180.0) % 360.0 - 180.0


def compass_point(bearing: float) -> str:
  """8-point compass direction for a bearing in degrees."""
  return COMPASS_POINTS[int(((bearing % 360.0) + 22.5) // 45.0) % 8]
