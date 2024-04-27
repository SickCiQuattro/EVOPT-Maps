import math

def euclidean_distance(node_a, node_b, graph): # distanza euclidea tra due nodi
    x1, y1 = graph.nodes[node_a]['x'], graph.nodes[node_a]['y'] # coordinate geografiche deciamli del nodo_a
    x2, y2 = graph.nodes[node_b]['x'], graph.nodes[node_b]['y'] # coordinate geografiche deciamli del nodo_b
    return haversine_distance(y1, x1, y2, x2)

def time_based_heuristic(node_a, node_b, graph):
    # Stima il tempo per raggiungere node_b da node_a
    if graph.has_edge(node_a, node_b):
        # Calcola il tempo medio di viaggio tra i nodi considerando tutti i collegamenti (edges)
        total_time = 0
        edge_count = 0
        for key in graph[node_a][node_b]:
            total_time += graph[node_a][node_b][key]['travel_time']
            edge_count += 1
        if edge_count > 0:
            average_time = total_time / edge_count
            return average_time / 3600  # Converti in ore
    else:
        # Se non c'è un collegamento diretto, stima il tempo basandosi su una velocità media
        average_speed_kph = 50
        distance_km = euclidean_distance(node_a, node_b, graph)
        estimated_time_hours = distance_km / average_speed_kph
        return estimated_time_hours

def blind(start, goal) -> int:
    return 0

def haversine_distance(lat1, lon1, lat2, lon2):
    # Raggio della Terra in km
    R = 6371.0

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

def adaptive_heuristic(node_a, node_b, graph, shortest_path):
    # Stima adattiva del tempo per raggiungere node_b da node_a
    if graph.has_edge(node_a, node_b):
        # Calcola il tempo medio di viaggio tra i nodi considerando solo i collegamenti del percorso più breve
        total_time = 0
        edge_count = 0
        for key in shortest_path:
            if graph.has_edge(key, node_b):
                total_time += graph[key][node_b][0]['travel_time']
                edge_count += 1
        if edge_count > 0:
            average_time = total_time / edge_count
            return average_time / 3600  # Converti in ore
    else:
        # Se non c'è un collegamento diretto, stima il tempo basandosi su una velocità media
        average_speed_kph = 50
        distance_km = euclidean_distance(node_a, node_b, graph)
        estimated_time_hours = distance_km / average_speed_kph
        return estimated_time_hours