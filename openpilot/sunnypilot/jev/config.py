"""
Jev settings live in a JSON file so this stays Python-only on prebuilt branches (new Params keys
would need a rebuild). Keys never go in the repo.

/data/jev/config.json:
  {"enabled": true, "typesafe_api_key": "...", "mapbox_token": "..."}   # both keys optional
"""
import json
from pathlib import Path

CONFIG_PATH = Path("/data/jev/config.json")


def load(path: Path = CONFIG_PATH) -> dict:
  try:
    data = json.loads(path.read_text())
  except (OSError, ValueError):
    return {}
  return data if isinstance(data, dict) else {}


def enabled(path: Path = CONFIG_PATH) -> bool:
  """The map rule runs without a Jev key; Jev is asked only when typesafe_api_key is set."""
  return bool(load(path).get("enabled"))
