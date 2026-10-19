import io
import re
import urllib.error

import networkx as nx
import numpy as np
import pytest
from PIL import Image

from evopt import elevation
from evopt.elevation import Dem, add_node_elevations, decode

Z = 12
ORIGIN_X = 2147 * 256  # global start column of the test area (Piedmont)


def encode(elev):
    """Elevations (256x256, metres) in Terrarium format: R*256 + G + B/256 - 32768."""
    v = np.asarray(elev, dtype=np.float64) + 32768
    r = np.floor(v / 256)
    g = np.floor(v - r * 256)
    b = np.floor((v - np.floor(v)) * 256)
    img = Image.fromarray(np.stack([r, g, b], axis=-1).astype(np.uint8), "RGB")
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


def slope_fetch(calls):
    """Terrain rising 0.01 m per pixel eastwards, continuous across adjacent tiles."""

    def fetch(url):
        z, x, y = map(int, re.search(r"/(\d+)/(\d+)/(\d+)\.png$", url).groups())
        calls.append((z, x, y))
        cols = (x * 256 + np.arange(256)) - ORIGIN_X
        return encode(np.tile(0.01 * cols, (256, 1)))

    return fetch


def test_decode_recovers_elevations_including_below_sea_level():
    want = np.full((256, 256), 1234.5)
    want[0, 0], want[1, 1] = -10.25, 0.0
    got = decode(encode(want))
    assert np.allclose(got, want, atol=1 / 256 + 1e-9)


def test_bilinear_sampling_is_exact_on_a_linear_slope_even_across_a_tile_edge(tmp_path):
    calls = []
    dem = Dem(tmp_path, fetch=slope_fetch(calls))
    for x_global in (
        ORIGIN_X + 100.3,
        ORIGIN_X + 255.6,
        ORIGIN_X + 256.2,
    ):  # the last one is in the neighbouring tile
        lat, lon = elevation.lat_lon(x_global, 2147 * 0 + 1455 * 256 + 100.0, Z)
        assert dem.at(lat, lon) == pytest.approx(0.01 * (x_global - 0.5 - ORIGIN_X), abs=0.01)
    assert {c[1] for c in calls} >= {2147, 2148}


def graph_over_area():
    G = nx.MultiDiGraph()
    for n, x in enumerate((ORIGIN_X + 20.0, ORIGIN_X + 120.0, ORIGIN_X + 400.0)):
        lat, lon = elevation.lat_lon(x, 1455 * 256 + 50.0, Z)
        G.add_node(n, x=lon, y=lat)
    G.add_edge(0, 1)
    return G


def test_nodes_get_their_elevation_and_tiles_are_cached_on_disk(tmp_path):
    G, calls = graph_over_area(), []
    add_node_elevations(G, tmp_path, fetch=slope_fetch(calls))
    assert [round(G.nodes[n]["elevation"], 1) for n in range(3)] == pytest.approx([0.2, 1.2, 4.0], abs=0.1)
    first = len(calls)
    assert first >= 2  # several tiles: the third node lies beyond the edge of the first

    again = graph_over_area()
    add_node_elevations(again, tmp_path, fetch=slope_fetch(calls))  # same folder: everything from disk
    assert len(calls) == first
    assert again.nodes[2]["elevation"] == pytest.approx(G.nodes[2]["elevation"])


def test_nodes_that_already_have_an_elevation_are_left_alone(tmp_path):
    G, calls = graph_over_area(), []
    for n in G.nodes:
        G.nodes[n]["elevation"] = 99.0
    add_node_elevations(G, tmp_path, fetch=slope_fetch(calls))
    assert calls == [] and all(G.nodes[n]["elevation"] == 99.0 for n in G.nodes)


def test_a_failed_download_is_an_oserror_and_leaves_the_graph_unchanged(tmp_path):
    def down(url):
        raise urllib.error.URLError("offline")

    G = graph_over_area()
    with pytest.raises(OSError):
        add_node_elevations(G, tmp_path, fetch=down)
    assert not any("elevation" in d for _, d in G.nodes(data=True))


def chain(elevations):
    G = nx.MultiDiGraph()
    for i, e in enumerate(elevations):
        G.add_node(i, x=9.0, y=45.0, elevation=float(e))
        if i:
            G.add_edge(i - 1, i)
            G.add_edge(i, i - 1)
    return G


def test_smoothing_removes_noise_but_keeps_a_real_slope():
    from evopt.elevation import smooth

    ramp = chain([0, 10, 20, 30, 40, 50, 60])
    smooth(ramp, passes=3)
    assert [ramp.nodes[i]["elevation"] for i in range(7)] == pytest.approx([0, 10, 20, 30, 40, 50, 60])

    noisy = chain([100, 108, 100, 108, 100, 108, 100])  # a viaduct read as dips by the DEM
    smooth(noisy, passes=3)
    inner = [noisy.nodes[i]["elevation"] for i in range(1, 6)]
    assert max(inner) - min(inner) < 8  # the noise amplitude dropped


def test_smoothing_leaves_endpoints_and_isolated_nodes_alone():
    from evopt.elevation import smooth

    G = chain([5, 50, 10])
    G.add_node(9, x=9.0, y=45.0, elevation=777.0)
    smooth(G, passes=2)
    assert G.nodes[0]["elevation"] == 5 and G.nodes[2]["elevation"] == 10 and G.nodes[9]["elevation"] == 777
