"""Current outside temperature from Open-Meteo (free, no key)."""

import json
import urllib.parse
import urllib.request

URL = "https://api.open-meteo.com/v1/forecast"


def current_temperature(lat, lon, timeout=8):
    """Temperature (°C, rounded to a whole degree) now at the given point."""
    query = urllib.parse.urlencode(
        {"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}", "current": "temperature_2m"}
    )
    req = urllib.request.Request(f"{URL}?{query}", headers={"User-Agent": "evopt-maps"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return round(json.load(resp)["current"]["temperature_2m"])
