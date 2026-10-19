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


DC_SOCKETS = (
    "socket:chademo",
    "socket:type2_combo",
    "socket:ccs",
    "socket:tesla_supercharger",
    "socket:tesla_ccs",
)


@dataclass(frozen=True)
class Station:
    lat: float
    lon: float
    kw: float | None  # None se la fonte non indica la potenza
    label: str | None = None  # "operatore · nome", se la fonte li ha
    hint: float | None = None  # potenza stimata dalle prese, usata solo se kw manca


def _text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def label_of(tags):
    parts = [_text(tags.get("operator")) or _text(tags.get("brand")), _text(tags.get("name"))]
    return " \u00b7 ".join(p for p in parts if p) or None


def estimate_kw(tags):
    """Colonnine senza potenza: le prese in continua (CCS, CHAdeMO) indicano una ricarica rapida, circa 50 kW.

    shortcut: 50 kW è un valore prudente per la rapida; in alternata la potenza varia troppo per stimarla.
    """
    return 50.0 if any(_text(tags.get(k)) not in (None, "0", "no") for k in DC_SOCKETS) else None


def power_kw(tags):
    """Potenza massima dai tag OSM '*output' (es. '22 kW', '7,4 kW'). Si assume kW, come da convenzione OSM."""
    values = []
    for key, raw in tags.items():
        if key.endswith("output") and isinstance(raw, str) and (m := _NUMBER.match(raw.strip())):
            values.append(float(m.group().replace(",", ".")))
    return max(values, default=None)


def station_from_tags(lat, lon, tags):
    kw = power_kw(tags)
    return Station(lat, lon, kw, label_of(tags), None if kw is not None else estimate_kw(tags))


def osm_to_stations(gdf):
    stations = []
    for _, row in gdf.iterrows():
        p = row.geometry.representative_point()  # i poligoni (aree di ricarica) diventano un punto
        stations.append(station_from_tags(p.y, p.x, row.drop("geometry").to_dict()))
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
        stations.append(Station(a["Latitude"], a["Longitude"], max(kws, default=None), _text(a.get("Title"))))
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
    """OSM come base; potenza ed etichetta mancanti arrivano da OCM, le stazioni solo in OCM vengono aggiunte."""
    if not ocm:
        return list(osm)
    o_lat, o_lon = np.array([s.lat for s in osm]), np.array([s.lon for s in osm])
    c_lat, c_lon = np.array([c.lat for c in ocm]), np.array([c.lon for c in ocm])
    merged = []
    for s in osm:
        d = haversine_m(s.lat, s.lon, c_lat, c_lon)
        i = int(np.argmin(d))
        if d[i] <= match_m:
            c = ocm[i]
            s = Station(s.lat, s.lon, s.kw if s.kw is not None else c.kw, s.label or c.label, s.hint)
        merged.append(s)
    extra = [c for c in ocm if not len(osm) or haversine_m(c.lat, c.lon, o_lat, o_lon).min() > match_m]
    return merged + extra


def apply_stations(G, stations, default_kw=22.0, max_snap_m=200):
    """Marca i nodi più vicini con 'charger_kw'. Scarta le stazioni troppo lontane da una strada."""
    found = nearest_nodes(G, [(s.lat, s.lon) for s in stations])
    for s, (node, dist) in zip(stations, found):
        if dist <= max_snap_m:
            kw = s.kw if s.kw is not None else s.hint if s.hint is not None else default_kw
            if kw >= G.nodes[node].get("charger_kw", 0):
                G.nodes[node]["charger_kw"] = kw
                if s.label:
                    G.nodes[node]["charger_label"] = s.label


def save_stations(stations, path):
    Path(path).write_text(json.dumps([[s.lat, s.lon, s.kw, s.label, s.hint] for s in stations]))


def load_stations(path):
    return [Station(*row) for row in json.loads(Path(path).read_text())]
