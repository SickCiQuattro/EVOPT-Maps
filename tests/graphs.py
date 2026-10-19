import random

import networkx as nx

from evopt.graph import haversine_m


def grid(n, seed=1, speeds=(30, 50, 90)):
    """n×n grid of two-way roads at random speeds; length = real distance between nodes."""
    rnd = random.Random(seed)
    G = nx.MultiDiGraph()
    for i in range(n):
        for j in range(n):
            G.add_node(i * n + j, x=9.0 + j * 0.002, y=45.0 + i * 0.002)
    for i in range(n):
        for j in range(n):
            for di, dj in ((0, 1), (1, 0)):
                if i + di < n and j + dj < n:
                    a, b = i * n + j, (i + di) * n + (j + dj)
                    length = float(
                        haversine_m(G.nodes[a]["y"], G.nodes[a]["x"], G.nodes[b]["y"], G.nodes[b]["x"])
                    )
                    speed = float(rnd.choice(speeds))
                    for u, v in ((a, b), (b, a)):
                        G.add_edge(u, v, length=length, speed_kph=speed, travel_time=length / (speed / 3.6))
    return G
