import math
import osmnx as ox

def euclidean_distance(node_a, node_b, graph):
    """Calcola la distanza euclidea tra due nodi.

    Args:
        node_a (int): Il primo nodo.
        node_b (int): Il secondo nodo.
        graph (Graph): Il grafo che contiene i nodi.

    Returns:
        float: La distanza euclidea tra i due nodi.
    """
    x1, y1 = graph.nodes[node_a]['x'], graph.nodes[node_a]['y'] # coordinate geografiche deciamli del nodo_a
    x2, y2 = graph.nodes[node_b]['x'], graph.nodes[node_b]['y'] # coordinate geografiche deciamli del nodo_b
    return haversine_distance(y1, x1, y2, x2)

def time_based_heuristic(node_a, node_b, graph):
    """Calcola un'euristica basata sul tempo tra due nodi.

    Args:
        node_a (int): Il primo nodo.
        node_b (int): Il secondo nodo.
        graph (Graph): Il grafo che contiene i nodi.

    Returns:
        float: L'euristica basata sul tempo tra i due nodi in ore.
    """
    if graph.has_edge(node_a, node_b):
        total_time = graph[node_a][node_b]['travel_time']
        return total_time / 3600  # Converti in ore
    else: # Se non c'è un collegamento diretto, stima il tempo basandosi su una velocità media
        average_speed_kph = 50
        return euclidean_distance(node_a, node_b, graph) / average_speed_kph


def shortest_destination(node_a, node_b, graph):
    """Trova il percorso più breve tra due nodi utilizzando l'algoritmo di Dijkstra.

    Args:
        node_a (int): Il nodo di partenza.
        node_b (int): Il nodo di arrivo.
        graph (Graph): Il grafo che contiene i nodi.

    Returns:
        float: Il costo del percorso più breve tra i due nodi in ore.
    """
    short = ox.routing.shortest_path(graph, node_a, node_b, weight='travel_time', cpus=1)
    cost = sum(graph[i][j]['travel_time'] for i, j in zip(short[:-1], short[1:]))
    # cost = 0
    # for i in range(len(short) - 1):
    #     cost += graph[short[i]][short[i+1]]['travel_time']
    return cost / 3600

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcola la distanza haversine tra due punti geografici.

    Args:
        lat1 (float): La latitudine del primo punto.
        lon1 (float): La longitudine del primo punto.
        lat2 (float): La latitudine del secondo punto.
        lon2 (float): La longitudine del secondo punto.

    Returns:
        float: La distanza haversine in km tra i due punti.
    """
    R = 6371.0 # Raggio della Terra in km

    # Conversione delle coordinate da gradi decimali a radianti
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Differenze di coordinate
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Formula di Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c # Distanza in km
    
def blind(start, goal) -> int:
    """Una funzione euristica cieca che restituisce sempre 0.

    Args:
        start (int): Il nodo di partenza.
        goal (int): Il nodo di arrivo.

    Returns:
        int: Restituisce sempre 0.
    """
    return 0
