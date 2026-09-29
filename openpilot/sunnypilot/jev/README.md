# Jev experimental-mode switcher

Once a second `jevd` asks Jev (typesafe.ai) whether openpilot should drive end-to-end
("blended": stops for red lights and stop signs, slows for turns) or plain ACC. The planner
uses end-to-end when Dynamic Experimental Control **or** a Jev decision less than 2.5 s old
says so. Jev can only add end-to-end time; if it is off, slow or offline, DEC decides alone.

Map facts: the Mapbox route (traffic signals, stop signs, turns) when a destination file and a
Mapbox token exist, otherwise the bundled offline OpenStreetMap extract (`data/illinois_controls.json.gz`,
20,188 traffic signals and 44,825 stop signs, no network needed). Each second `jevd` publishes
end-to-end if a network-free map rule (a light / stop sign within max(150 m, 8 s)) OR Jev says so,
so it works with no Jev key and no internet. Other states: put an extract at
`/data/jev/osm_controls.json.gz` (same format).

Evaluated on 20 of the owner's recorded drives (11 h): end-to-end over the whole approach to
126 of 128 lights / stop signs where the driver stopped (DEC alone: 68), 4.6% of open road.

## Setup on the device

1. Install this branch: `installer.comma.ai/bhartiyashesh/jev-staging`.
2. Turn on **Experimental Mode** and **Cruise > Enable Dynamic Experimental Control**
   (the switcher works inside DEC). Optional: **Smart Cruise Control - Vision / Map**.
3. Over SSH, create the settings file (keys stay on the device, never in git):

   ```sh
   mkdir -p /data/jev
   cat > /data/jev/config.json <<'JSON'
   {"enabled": true, "typesafe_api_key": "YOUR_JEV_KEY", "mapbox_token": "YOUR_MAPBOX_TOKEN"}
   JSON
   ```

   Both keys are optional (`{"enabled": true}` runs the offline map rule alone). `jevd` starts on the next drive. Set `"enabled": false` to turn it off.
4. Optional destination for the Mapbox route (otherwise the offline OpenStreetMap map is used).
   From a computer on the same network as the device:

   ```sh
   python openpilot/sunnypilot/jev/set_destination.py "233 S Wacker Dr, Chicago, IL" --host comma@<device-ip>
   python openpilot/sunnypilot/jev/set_destination.py --clear --host comma@<device-ip>
   ```

   It shows the Mapbox match and asks before writing `/data/jev/destination.json`. Street addresses
   work, landmark names do not; `"lat,lon"` also works.

Decisions are logged to `/data/jev/log/*.jsonl`. The car needs internet (Wi-Fi or cellular).

## Compass

The mici onroad HUD shows the direction of travel (N, NE, E, SE, S, SW, W, NW) in the top right
corner, from the GPS course. It keeps the last direction while stopped.

## Data license

`data/illinois_controls.json.gz`: data (c) OpenStreetMap contributors, available under the Open
Database License 1.0 (https://www.openstreetmap.org/copyright).
