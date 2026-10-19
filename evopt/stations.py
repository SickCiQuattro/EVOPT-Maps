import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import osmnx as ox
from osmnx._errors import InsufficientResponseError

from evopt.graph import haversine_m, nearest_nodes

OCM_URL = "https://api.openchargemap.io/v3/poi"
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass(frozen=True)
class Station:
    lat: float
    lon: float
    kw: float | None  # None se la fonte non indica la potenza


def power_kw(tags):
    """Potenza massima dai tag OSM '*output' (es. '22 kW', '7,4 kW'). Si assume kW, come da convenzione OSM."""
    values = []
    for key, raw in tags.items():
        if key.endswith("output") and isinstance(raw, str) and (m := _NUMBER.match(raw.strip())):
            values.append(float(m.group().replace(",", ".")))
    return max(values, default=None)


def osm_to_stations(gdf):
    stations = []
    for _, row in gdf.iterrows():
        p = row.geometry.representative_point()  # i poligoni (aree di ricarica) diventano un punto
        stations.append(Station(p.y, p.x, power_kw(row.drop("geometry").to_dict())))
    return stations


def fetch_osm(place):
    try:
        gdf = ox.features_from_place(place, tags={"amenity": "charging_station"})
    except InsufficientResponseError:
        return []
    return osm_to_stations(gdf)


def parse_ocm(items):
    stations = []
    for item in items:
        a = item.get("AddressInfo") or {}
        if a.get("Latitude") is None or a.get("Longitude") is None:
            continue
        kws = [c["PowerKW"] for c in item.get("Connections") or [] if c.get("PowerKW") is not None]
        stations.append(Station(a["Latitude"], a["Longitude"], max(kws, default=None)))
    return stations


def fetch_ocm(lat, lon, radius_km, api_key=None, max_results=1000):
    key = api_key or os.environ.get("OCM_API_KEY")
    if not key:
        raise ValueError("serve una chiave Open Charge Map: passa api_key o imposta OCM_API_KEY")
    query = urllib.parse.urlencode(
        {
            "output": "json",
            "latitude": lat,
            "longitude": lon,
            "distance": radius_km,
            "distanceunit": "KM",
            "maxresults": max_results,
            "compact": "true",
            "verbose": "false",
            "key": key,
        }
    )
    req = urllib.request.Request(f"{OCM_URL}?{query}", headers={"User-Agent": "evopt-maps"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return parse_ocm(json.load(resp))


def merge(osm, ocm, match_m=100):
    """OSM come base; la potenza mancante arriva da OCM, le stazioni solo in OCM vengono aggiunte."""
    if not ocm:
        return list(osm)
    lats = np.array([s.lat for s in ocm])
    lons = np.array([s.lon for s in ocm])
    merged = []
    for s in osm:
        d = haversine_m(s.lat, s.lon, lats, lons)
        i = int(np.argmin(d))
        if s.kw is None and d[i] <= match_m:
            s = Station(s.lat, s.lon, ocm[i].kw)
        merged.append(s)
    return merged + [s for s in ocm if not _near(s, osm, match_m)]


def _near(s, others, match_m):
    return any(haversine_m(s.lat, s.lon, np.array([o.lat]), np.array([o.lon]))[0] <= match_m for o in others)


def apply_stations(G, stations, default_kw=22.0, max_snap_m=200):
    """Marca i nodi più vicini con 'charger_kw'. Scarta le stazioni troppo lontane da una strada."""
    found = nearest_nodes(G, [(s.lat, s.lon) for s in stations])
    for s, (node, dist) in zip(stations, found):
        if dist <= max_snap_m:
            kw = s.kw if s.kw is not None else default_kw
            G.nodes[node]["charger_kw"] = max(kw, G.nodes[node].get("charger_kw", 0))


def save_stations(stations, path):
    Path(path).write_text(json.dumps([[s.lat, s.lon, s.kw] for s in stations]))


def load_stations(path):
    return [Station(*row) for row in json.loads(Path(path).read_text())]
