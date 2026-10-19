"""Estrae da un file OSM locale (.pbf, es. Geofabrik) una rete stradale e le stazioni di ricarica per un'area.

Niente Overpass: serve per testare viaggi realistici su aree grandi.

    uv run --with osmium python -m benchmarks.extract data/nord-ovest.osm.pbf \\
        --bbox 7.4 44.9 9.5 45.7 --name milano-torino

Scrive data/<name>.graphml (strade) e data/<name>-stations.json. La rete tiene solo le strade principali
(autostrade, superstrade, strade statali e provinciali) e contrae i nodi che non sono incroci.
"""

import argparse
import itertools
from collections import Counter
from pathlib import Path

import networkx as nx
import osmium
import osmnx as ox
from shapely.geometry import LineString

from evopt.graph import haversine_m
from evopt.stations import Station, power_kw, save_stations

DEFAULT_KPH = {
    "motorway": 130, "motorway_link": 60, "trunk": 90, "trunk_link": 50,
    "primary": 70, "primary_link": 40, "secondary": 60, "secondary_link": 40,
}  # fmt: skip


def _speed(tags):
    raw = tags.get("maxspeed", "")
    digits = "".join(c for c in raw.split()[0] if c.isdigit()) if raw else ""
    return float(digits) if digits and "mph" not in raw else float(DEFAULT_KPH[tags["highway"]])


def _oneway(tags):
    return tags.get("oneway") == "yes" or tags["highway"] in ("motorway", "motorway_link")


def read(pbf, bbox):
    west, south, east, north = bbox
    inside = lambda loc: west <= loc.lon <= east and south <= loc.lat <= north
    ways, stations = [], []
    for obj in (
        osmium.FileProcessor(pbf).with_locations().with_filter(osmium.filter.KeyFilter("highway", "amenity"))
    ):
        tags = dict(obj.tags)
        if obj.is_way() and tags.get("highway") in DEFAULT_KPH:
            pts = [(n.ref, n.location.lon, n.location.lat) for n in obj.nodes if n.location.valid()]
            if len(pts) >= 2 and any(west <= x <= east and south <= y <= north for _, x, y in pts):
                ways.append((pts, tags))
        elif tags.get("amenity") == "charging_station":
            loc = (
                obj.location
                if obj.is_node()
                else (obj.nodes[0].location if obj.is_way() and obj.nodes else None)
            )
            if loc is not None and loc.valid() and inside(loc):
                stations.append(Station(loc.lat, loc.lon, power_kw(tags)))
    return ways, stations


def build(ways):
    """Grafo orientato: un arco per tratto tra due incroci, con lunghezza, velocità, tempo e geometria."""
    uses = Counter(ref for pts, _ in ways for ref, _, _ in pts)
    G = nx.MultiDiGraph(crs="epsg:4326")
    for pts, tags in ways:
        kph = _speed(tags)
        keep = [i for i, (ref, _, _) in enumerate(pts) if i in (0, len(pts) - 1) or uses[ref] > 1]
        for a, b in itertools.pairwise(keep):
            seg = pts[a : b + 1]
            length = sum(float(haversine_m(p[2], p[1], q[2], q[1])) for p, q in itertools.pairwise(seg))
            if length <= 0:
                continue
            geom = LineString([(x, y) for _, x, y in seg])
            for ref, x, y in (seg[0], seg[-1]):
                G.add_node(ref, x=x, y=y)
            edge = {"length": length, "speed_kph": kph, "travel_time": length / (kph / 3.6), "geometry": geom}
            G.add_edge(seg[0][0], seg[-1][0], **edge)
            if not _oneway(tags):
                G.add_edge(
                    seg[-1][0], seg[0][0], **(edge | {"geometry": LineString(list(geom.coords)[::-1])})
                )
    # componente fortemente connessa maggiore: il resto sono isole che non servono a nessun viaggio
    core = max(nx.strongly_connected_components(nx.DiGraph(G)), key=len)
    return G.subgraph(core).copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pbf")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"), required=True)
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    ways, stations = read(args.pbf, args.bbox)
    print(
        f"{len(ways)} ways, {len(stations)} charging stations ({sum(s.kw is not None for s in stations)} with power)"
    )
    G = build(ways)
    out = Path("data")
    ox.save_graphml(G, out / f"{args.name}.graphml")
    save_stations(stations, out / f"{args.name}-stations.json")
    print(f"graph: {len(G)} nodes, {G.number_of_edges()} edges -> {out / args.name}.graphml")


if __name__ == "__main__":
    main()
