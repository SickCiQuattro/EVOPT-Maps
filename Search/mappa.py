import osmnx as ox
import networkx as nx
import random
import math

ox.settings.use_cache = True

# G = ox.graph_from_place('Milan, Italy', network_type='drive')  # Scarica i dati della rete stradale da OSM
G = ox.graph_from_point((45.89, 10.18), 1000 , network_type='drive') # Scarica i dati della rete stradale da OSM
print("Grafo generato con", len(G.nodes()), "nodi e", len(G.edges()), "archi")

# Aggiungi velocità e tempi di percorrenza agli archi
G = ox.routing.add_edge_speeds(G) # Aggiungi velocità agli archi in km/h 'speed_kph'
G = ox.routing.add_edge_travel_times(G) # Aggiungi tempi di percorrenza agli archi in secondi s 'travel_time'
G = ox.distance.add_edge_lengths(G) # Aggiungi lunghezze degli archi in metri m 'length'



# Aggiungi stazioni di ricarica casuali se non sono già presenti
all_nodes = list(G.nodes) # Lista di tutti i nodi
charging_stations = random.sample(all_nodes, 20) # Scegli un numero casuale di stazioni di ricarica
# G = ox.utils_graph.convert.to_digraph(G, weight="travel_time") # Converte MultiDiGraph in DiGraph
    
for node in charging_stations: # Imposta le stazioni di ricarica casuali
    G.nodes[node]['charging_station'] = True

x_values = [G.nodes[node]['x'] for node in G.nodes]
y_values = [G.nodes[node]['y'] for node in G.nodes]
min_x, max_x = min(x_values), max(x_values)
min_y, max_y = min(y_values), max(y_values)
# Imposta l'attributo 'pos' per ogni nodo (necessario per disegnare il grafo)
for node in G.nodes:
    # Normalizza le coordinate in modo che si adattino alla finestra di Pygame
    x = (G.nodes[node]['x'] - min_x) / (max_x - min_x) * 800
    y = (G.nodes[node]['y'] - min_y) / (max_y - min_y) * 600
    G.nodes[node]['pos'] = (int(x), int(y))

for u, v, k, data in G.edges(keys=True, data=True):
    print(u, v, k, data)

for node in G.nodes():
    print(node, G.nodes[node])

# print(G.nodes[11778564649])
# print(G.edges[11778564649, 877603872, 0])
print("Grafo generato con", len(G.nodes()), "nodi e", len(G.edges()), "archi")

#print(G.edges[11779835693, 867256802, 0]['travel_time'])

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

    # Distanza in km
    distance = R * c
    return distance * 1000

#x1, y1 = G.nodes[11779835693]['x'], G.nodes[11779835693]['y'] # coordinate geografiche deciamli del nodo_a
#x2, y2 = G.nodes[867256802]['x'], G.nodes[867256802]['y'] # coordinate geografiche deciamli del nodo_b
   

#print(f"Distanza: {haversine_distance(y1, x1, y2, x2)} km")

# 11779835693 867256802 'length': 72.279
# 11779835693 {'y': 45.8918293, 'x': 10.1569247
# 867256802 {'y': 45.891577, 'x': 10.1577854
#877603949 1760984660
#877604045 1760984660