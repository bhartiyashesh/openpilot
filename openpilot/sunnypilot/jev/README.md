# Jev experimental-mode switcher

Once a second `jevd` asks Jev (typesafe.ai) whether openpilot should drive end-to-end
("blended": stops for red lights and stop signs, slows for turns) or plain ACC. The planner
uses end-to-end when Dynamic Experimental Control **or** a Jev decision less than 2.5 s old
says so. Jev can only add end-to-end time; if it is off, slow or offline, DEC decides alone.

Map facts: the Mapbox route (traffic signals, stop signs, turns) when a destination file and a
Mapbox token exist, otherwise OpenStreetMap signals and stop signs ahead of the car's heading.

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

   `jevd` starts on the next drive. Set `"enabled": false` to turn it off.
4. Optional destination for the Mapbox route (otherwise OpenStreetMap is used):

   ```sh
   echo '{"lat": 42.0419, "lon": -87.7797}' > /data/jev/destination.json
   ```

Decisions are logged to `/data/jev/log/*.jsonl`. The car needs internet (Wi-Fi or cellular).

## Compass

The mici onroad HUD shows the direction of travel (N, NE, E, SE, S, SW, W, NW) in the top right
corner, from the GPS course. It keeps the last direction while stopped.
