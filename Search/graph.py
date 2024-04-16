import networkx as nx
import json
import random

# Genera un grafo casuale
def generate_random_graph(num_nodes, num_edges, num_charging_stations):
    G = nx.gnm_random_graph(num_nodes, num_edges)
    charging_stations = random.sample(G.nodes(), num_charging_stations)
    for node in charging_stations:
        G.nodes[node]['charging_station'] = True
    return G

# Esporta il grafo in un file .json
def export_graph_to_json(graph, file_name):
    data = nx.node_link_data(graph)
    with open(file_name, 'w') as f:
        json.dump(data, f)

# Numero di nodi, archi e stazioni di ricarica
num_nodes = 10
num_edges = 15
num_charging_stations = 3

# Genera e esporta il grafo
graph = generate_random_graph(num_nodes, num_edges, num_charging_stations)
export_graph_to_json(graph, 'graph.json')