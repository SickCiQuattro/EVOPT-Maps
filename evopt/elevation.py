"""Quota dei nodi da tile Terrarium (AWS Open Data, senza chiave né login).

Ogni tile è un PNG 256x256 in cui R, G e B codificano la quota: R*256 + G + B/256 - 32768 metri.
Risoluzione circa 30 m al livello 12, la stessa delle fonti da cui derivano (SRTM tra le altre).
"""

import math
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
ZOOM = 12
SIZE = 256


def _http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "evopt-maps"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def pixel(lat, lon, z=ZOOM):
    """Coordinate continue in pixel globali (Web Mercator) di un punto."""
    n = SIZE * 2**z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def lat_lon(px, py, z=ZOOM):
    n = SIZE * 2**z
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * py / n)))), px / n * 360 - 180


def decode(png_bytes):
    import io

    rgb = np.asarray(Image.open(io.BytesIO(png_bytes)).convert("RGB"), dtype=np.float32)
    return rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768


class Dem:
    """Campionatore di quote con tile scaricati una volta e tenuti in `cache_dir/dem`."""

    def __init__(self, cache_dir, zoom=ZOOM, fetch=None):
        self.dir, self.z, self.fetch = Path(cache_dir) / "dem", zoom, fetch or _http_get
        self._tiles = {}

    def tile(self, tx, ty):
        if (tx, ty) not in self._tiles:
            path = self.dir / str(self.z) / str(tx) / f"{ty}.png"
            if path.exists():
                data = path.read_bytes()
            else:
                data = self.fetch(TILE_URL.format(z=self.z, x=tx, y=ty))
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(f".{os.getpid()}.tmp")
                tmp.write_bytes(data)
                tmp.replace(path)  # mai un file a metà in cache
            self._tiles[(tx, ty)] = decode(data)
        return self._tiles[(tx, ty)]

    def _px(self, ix, iy):
        return float(self.tile(ix // SIZE, iy // SIZE)[iy % SIZE, ix % SIZE])

    def at(self, lat, lon):
        """Quota in metri, interpolando bilinearmente tra i centri dei quattro pixel vicini."""
        x, y = pixel(lat, lon, self.z)
        fx, fy = x - 0.5, y - 0.5
        x0, y0 = math.floor(fx), math.floor(fy)
        dx, dy = fx - x0, fy - y0
        top = self._px(x0, y0) * (1 - dx) + self._px(x0 + 1, y0) * dx
        bottom = self._px(x0, y0 + 1) * (1 - dx) + self._px(x0 + 1, y0 + 1) * dx
        return top * (1 - dy) + bottom * dy

    def tiles_for(self, lat, lon):
        x, y = pixel(lat, lon, self.z)
        x0, y0 = math.floor(x - 0.5), math.floor(y - 0.5)
        return {((x0 + i) // SIZE, (y0 + j) // SIZE) for i in (0, 1) for j in (0, 1)}


def add_node_elevations(G, cache_dir, fetch=None, zoom=ZOOM, workers=8):
    """Imposta 'elevation' (m) sui nodi che ne sono privi. Se un tile non si scarica, il grafo resta com'era."""
    todo = [n for n, d in G.nodes(data=True) if "elevation" not in d]
    if not todo:
        return
    dem = Dem(cache_dir, zoom, fetch)
    needed = set()
    for n in todo:
        needed |= dem.tiles_for(G.nodes[n]["y"], G.nodes[n]["x"])
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(lambda t: dem.tile(*t), sorted(needed)))  # propaga l'OSError di un download fallito
    values = {n: round(dem.at(G.nodes[n]["y"], G.nodes[n]["x"]), 1) for n in todo}
    for n, v in values.items():
        G.nodes[n]["elevation"] = v
