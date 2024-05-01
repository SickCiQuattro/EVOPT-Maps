import folium
import osmnx as ox
import random
import time
from path_finding import PathFinding
from electric_vehicle import ElectricVehicleAStar
from heuristics import shortest_destination
import numpy as np

def generate_osm_graph(location, dist, network_type, num_charging_stations):
    # Genera un grafo da OpenStreetMap
    G = ox.graph_from_point(location, dist=dist, network_type=network_type)
    G = ox.routing.add_edge_speeds(G)
    G = ox.routing.add_edge_travel_times(G)
    G = ox.distance.add_edge_lengths(G)

    # Aggiungi stazioni di ricarica casuali
    all_nodes = list(G.nodes)
    charging_stations = random.sample(all_nodes, num_charging_stations)
    G = ox.utils_graph.convert.to_digraph(G, weight="travel_time") # Converte MultiDiGraph in DiGraph
    G = G.to_undirected() # Converte in un grafo non diretto
    for node in charging_stations:
        G.nodes[node]['charging_station'] = True

    return G, charging_stations

def draw_solution_on_map(graph, solution):
    # Crea una mappa centrata sulla posizione media dei nodi
    location = np.mean([graph.nodes[node]['pos'] for node in graph.nodes], axis=0)
    m = folium.Map(location=location, zoom_start=14)

    # Disegna il percorso sulla mappa
    for action in solution:
        start_pos = graph.nodes[action[0]]['pos']
        end_pos = graph.nodes[action[1]]['pos']
        folium.PolyLine(locations=[start_pos, end_pos], color="red", weight=2.5, opacity=1).add_to(m)

    return m



def main():
    start_time = time.time()
    # Impostazioni iniziali
    max_battery_capacity = 50   # Imposta la capacità massima della batteria in kWh
    min_battery_at_goal = 20     # Imposta la batteria minima di arrivo in %
    ambient_temperature = 20     # Imposta la temperatura ambientale
    location_point = (37.79, -122.41) # Esempio: San Francisco
    num_charging_stations = 40 # Numero di stazioni di ricarica
    min_battery_percent = max_battery_capacity * min_battery_at_goal / 100 # Batteria minima in percentuale
    # Genera il grafo e le stazioni di ricarica
    G, charging_stations = generate_osm_graph(location_point, 3000, 'drive', num_charging_stations)

    # Scegli un nodo di partenza e di arrivo casuale
    nodes_list = list(G.nodes())
    start_node = random.choice(nodes_list)
    end_node = random.choice(nodes_list)


    # Inizializza l'algoritmo di ricerca
    problem = PathFinding(G, start_node, end_node, [node for node in G.nodes() if G.nodes[node].get('charging_station', False)], min_battery_percent)
    # Inizializza l'algoritmo di ricerca A*
    astar = ElectricVehicleAStar(G, heuristic=lambda node_a, node_b, graph=G: shortest_destination(node_a, node_b, G), view=True, battery_capacity=max_battery_capacity, min_battery=min_battery_percent, temperature=ambient_temperature)


    # Inizia la ricerca
    print("tempo inizio ricerca", time.time()-start_time)
    solution = astar.solve(problem)
    print("tempo fine ricerca", time.time()-start_time)
    if solution:
        m = draw_solution_on_map(G, solution)
        # Salva la mappa come HTML
        m.save("path.html")
    else:    
        print("Percorso non trovato")

    print("Soluzione:", solution)
    print("Percorso trovato con", len(solution), "azioni")
    print("Fine simulazione")

# Esegui la funzione main
if __name__ == "__main__":
    main()
