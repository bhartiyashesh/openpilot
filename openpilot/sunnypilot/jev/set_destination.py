#!/usr/bin/env python3
"""
Set (or clear) the Jev navigation destination on the car from a computer.

  python set_destination.py "233 S Wacker Dr, Chicago, IL" --host comma@192.168.1.20
  python set_destination.py "41.8789,-87.6359" --host comma@192.168.1.20
  python set_destination.py --clear --host comma@192.168.1.20

Use a street address (the Mapbox geocoder does not know landmark names) or "lat,lon". The match
is shown and must be confirmed. Token: --token or MAPBOX_TOKEN. Writes
/data/jev/destination.json on the device over SSH. jevd picks it up within a few seconds and
switches to the Mapbox route; clearing it goes back to the offline OpenStreetMap map.
"""
import argparse
import json
import os
import subprocess
import urllib.parse
import urllib.request

GEOCODE_URL = "https://api.mapbox.com/search/geocode/v6/forward"
REMOTE_PATH = "/data/jev/destination.json"


def parse_geocode(data: dict) -> tuple[float, float, str]:
  """(lat, lon, name) of the best match."""
  feature = data["features"][0]
  lon, lat = feature["geometry"]["coordinates"]
  return float(lat), float(lon), feature.get("properties", {}).get("full_address") or feature.get("properties", {}).get("name", "")


def parse_coordinates(text: str) -> tuple[float, float] | None:
  """(lat, lon) if the text is "lat,lon", else None."""
  parts = text.split(",")
  try:
    lat, lon = (float(x) for x in parts)
  except ValueError:
    return None
  return (lat, lon) if len(parts) == 2 and -90 <= lat <= 90 and -180 <= lon <= 180 else None


def geocode(address: str, token: str) -> tuple[float, float, str]:
  query = urllib.parse.urlencode({"q": address, "limit": 1, "access_token": token})
  with urllib.request.urlopen(f"{GEOCODE_URL}?{query}", timeout=15) as response:
    return parse_geocode(json.load(response))


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("address", nargs="?")
  parser.add_argument("--host", required=True, help="ssh target, e.g. comma@192.168.1.20")
  parser.add_argument("--token", default=os.environ.get("MAPBOX_TOKEN"))
  parser.add_argument("--clear", action="store_true")
  args = parser.parse_args()
  if args.clear:
    subprocess.run(["ssh", args.host, f"rm -f {REMOTE_PATH}"], check=True)
    print("destination cleared (offline OpenStreetMap map in use)")
    return
  if not args.address:
    parser.error("an address or lat,lon is needed")
  coordinates = parse_coordinates(args.address)
  if coordinates is not None:
    (lat, lon), name = coordinates, args.address
  else:
    if not args.token:
      parser.error("a Mapbox token (--token or MAPBOX_TOKEN) is needed for addresses")
    lat, lon, name = geocode(args.address, args.token)
    if input(f"Mapbox matched: {name} ({lat:.5f}, {lon:.5f}). Use it? [y/N] ").strip().lower() != "y":
      print("not set")
      return
  payload = json.dumps({"lat": round(lat, 6), "lon": round(lon, 6), "name": name})
  subprocess.run(["ssh", args.host, f"mkdir -p /data/jev && cat > {REMOTE_PATH}"], input=payload.encode(), check=True)
  print(f"destination set: {name} ({lat:.5f}, {lon:.5f})")


if __name__ == "__main__":
  main()
