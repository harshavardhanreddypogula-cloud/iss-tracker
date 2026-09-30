"""
Asteria ISS Tracker
A tiny live tracker for the International Space Station.

- Python standard library only (nothing to pip install)
- Run:  python app.py
- Open: http://localhost:8000
"""

import json
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8000

# Two free public APIs. If the first one fails, we try the second.
SOURCES = [
    "https://api.wheretheiss.at/v1/satellites/25544",
    "http://api.open-notify.org/iss-now.json",
]


def fetch_iss():
    """Return the ISS position as a dict, or None if every source fails."""
    for url in SOURCES:
        try:
            with urllib.request.urlopen(url, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "latitude" in data:  # wheretheiss.at format
                return {
                    "lat": float(data["latitude"]),
                    "lon": float(data["longitude"]),
                    "alt_km": round(float(data["altitude"]), 1),
                    "speed_kmh": round(float(data["velocity"]), 1),
                }
            pos = data["iss_position"]  # open-notify format
            return {
                "lat": float(pos["latitude"]),
                "lon": float(pos["longitude"]),
                "alt_km": None,
                "speed_kmh": None,
            }
        except Exception as err:
            print("Source failed:", url, err)
    return None


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Asteria ISS Tracker</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body { margin: 0; font-family: Arial, sans-serif; background: #0b1020; color: #e8ecff; }
  header { padding: 12px 16px; background: #141a33; }
  header h1 { margin: 0; font-size: 20px; }
  header p { margin: 4px 0 0; font-size: 13px; color: #9aa4d6; }
  #stats { display: flex; flex-wrap: wrap; gap: 10px; padding: 10px 16px; }
  .card { background: #1b2345; border-radius: 8px; padding: 8px 14px; min-width: 110px; }
  .card span { display: block; font-size: 12px; color: #9aa4d6; }
  .card b { font-size: 18px; }
  #map { height: 65vh; }
  #status { padding: 6px 16px; font-size: 12px; color: #9aa4d6; }
</style>
</head>
<body>
<header>
  <h1>Asteria ISS Tracker</h1>
  <p>Live position of the International Space Station, updated every 5 seconds</p>
</header>
<div id="stats">
  <div class="card"><span>Latitude</span><b id="lat">-</b></div>
  <div class="card"><span>Longitude</span><b id="lon">-</b></div>
  <div class="card"><span>Altitude (km)</span><b id="alt">-</b></div>
  <div class="card"><span>Speed (km/h)</span><b id="spd">-</b></div>
</div>
<div id="map"></div>
<div id="status">Connecting...</div>

<script>
  const map = L.map('map').setView([0, 0], 2);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 6, attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const marker = L.marker([0, 0]).addTo(map).bindPopup('International Space Station');
  const trail = L.polyline([], { color: 'red', weight: 2 }).addTo(map);
  let first = true;

  async function update() {
    try {
      const res = await fetch('/api/iss');
      const d = await res.json();
      if (d.error) throw new Error(d.error);
      marker.setLatLng([d.lat, d.lon]);
      trail.addLatLng([d.lat, d.lon]);
      if (first) { map.setView([d.lat, d.lon], 3); first = false; }
      document.getElementById('lat').textContent = d.lat.toFixed(3);
      document.getElementById('lon').textContent = d.lon.toFixed(3);
      document.getElementById('alt').textContent = d.alt_km ?? 'n/a';
      document.getElementById('spd').textContent = d.speed_kmh ?? 'n/a';
      document.getElementById('status').textContent =
        'Last update: ' + new Date().toLocaleTimeString();
    } catch (e) {
      document.getElementById('status').textContent = 'Could not reach ISS data, retrying...';
    }
  }

  update();
  setInterval(update, 5000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/iss":
            data = fetch_iss() or {"error": "ISS data unavailable"}
            self._send(200, json.dumps(data).encode(), "application/json")
        elif self.path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain")

    def log_message(self, *args):
        pass  # keep the terminal quiet


if __name__ == "__main__":
    print(f"ISS tracker running at http://localhost:{PORT}  (Ctrl+C to stop)")
    HTTPServer(("", PORT), Handler).serve_forever()

