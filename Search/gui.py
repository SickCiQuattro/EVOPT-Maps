import folium
import osmnx as ox
import random
import time
import heuristics as h
from path_finding import PathFinding
from ASTAR import AStar
import numpy as np
from folium.plugins import MarkerCluster

# Funzione per generare un grafo da OpenStreetMap
def generate_osm_graph(location, dist, network_type, num_charging_stations):
    # Genera un grafo da OpenStreetMap
    # G = ox.graph_from_point(location, dist=dist, network_type=network_type, simplify=False)
    G = ox.graph_from_place('Timisoara', network_type='drive')  # Scarica i dati della rete stradale da OSM
    G = ox.routing.add_edge_speeds(G)
    G = ox.routing.add_edge_travel_times(G)
    G = ox.distance.add_edge_lengths(G)
    # Aggiungi stazioni di ricarica casuali
    all_nodes = list(G.nodes)
    # Scegli un numero casuale di stazioni di ricarica
    charging_stations = random.sample(all_nodes, num_charging_stations)
    G = ox.utils_graph.convert.to_digraph(G, weight="travel_time") # Converte MultiDiGraph in DiGraph
    #G = G.to_undirected() # Converte in un grafo non diretto
    for node in charging_stations:
        G.nodes[node]['charging_station'] = True

    return G, charging_stations

# Funzione per disegnare il percorso sulla mappa
def draw_solution_on_map(graph, solution, start_node, end_node, charging_stations):
    
    # Crea una mappa centrata sulla posizione media dei nodi
    location = np.mean([[graph.nodes[node]['y'], graph.nodes[node]['x']] for node in graph.nodes], axis=0)
    # Crea una mappa con folium
    m = folium.Map(location=location,tiles='CartoDB Positron', zoom_start=14)
    # Disegna il percorso sulla mappa
    for action in solution:
        start_pos = [graph.nodes[action[0]]['y'], graph.nodes[action[0]]['x']]
        end_pos = [graph.nodes[action[1]]['y'], graph.nodes[action[1]]['x']]
        folium.PolyLine(locations=[start_pos, end_pos], color="red", weight=2.5, opacity=1).add_to(m)
    # Aggiungi marcatori per il nodo di partenza e di destinazione
    folium.Marker(location=[graph.nodes[start_node]['y'], graph.nodes[start_node]['x']], popup='Start', icon=folium.Icon(color='blue',prefix='fa',icon='car')).add_to(m)
    folium.Marker(location=[graph.nodes[end_node]['y'], graph.nodes[end_node]['x']], popup='End', icon=folium.Icon(color='red', prefix='fa', icon='map-pin')).add_to(m)
    # Crea un oggetto MarkerCluster
    marker_cluster = MarkerCluster().add_to(m)
    # Aggiungi marcatori per tutte le stazioni di ricarica
    for station in charging_stations:
        folium.Marker(location=[graph.nodes[station]['y'], graph.nodes[station]['x']], popup='Charging Station', icon=folium.Icon(color='green', prefix='fa', icon='bolt')).add_to(marker_cluster)
    return m

def adaptive_search(graph, start, goal, min_battery_percent, max_battery_capacity, battery, ambient_temperature, electric_constant, path=[]):
    # Inizializza l'algoritmo di ricerca
    problem = PathFinding(graph, start, goal)
    # Inizializza l'algoritmo di ricerca A*
    astar = AStar(graph, h.euclidean_distance, view=True)
    solution = astar.solve(problem)
    print("soluzione", solution, "dim", len(solution))
    if solution is None:
        return None
    
    # if start.get('charging_station', False):
    #     # Se l'obiettivo è una stazione di ricarica, ricarica la batteria
    #     True

    # Calcola la distanza, la velocità e l'energia consumata
    distance = speed = 0
    for i, j in solution:
        distance += graph.edges[i, j].get('length', 10)
        speed += graph.edges[i, j].get('speed_kph', 50)
    # distance = sum(graph[i][j]['length'] for i, j in zip(solution[:-1], solution[1:]))
    # speed = sum(graph.edges[i, j].get('speed_kph', 50) for i, j in zip(solution[:-1], solution[1:]))
    energy_consumed = electric_constant * (distance / 1000) * speed / ambient_temperature

    # Se l'energia consumata è inferiore alla capacità massima della batteria, restituisci il percorso
    if energy_consumed < battery - min_battery_percent:
        # Aggiungi il percorso alla soluzione
        path += solution # se il nodo iniziale è uguale sostituisci, altrimenti cerca il nodo iniziale di soluzion in path e sostituisci da li
        return path

    max_distance = max_battery_capacity*ambient_temperature/(electric_constant*speed)
    # Altrimenti, trova la stazione di ricarica più vicina e richiama la funzione
    charging_station_start = nearest_charging_station(graph, start, goal, solution, max_distance * 0.8)
    if charging_station_start is not None:
        # Inizializza l'algoritmo di ricerca
        problem = PathFinding(graph, start, charging_station_start)
        # Inizializza l'algoritmo di ricerca A*
        astar = AStar(graph, h.euclidean_distance, view=True)
        solution = astar.solve(problem)
        if solution is None:
            return None
        path += solution
        battery = max_battery_capacity
        graph.nodes[charging_station_start]['charging_station'] = False

        return adaptive_search(graph, charging_station_start, goal, min_battery_percent, max_battery_capacity, battery, ambient_temperature, electric_constant, path)

    # Se non ci sono stazioni di ricarica raggiungibili, restituisci None
    return None

def nearest_charging_station(graph, start, goal, solution, raggio):
    # Ottieni tutte le stazioni di ricarica
    charging_stations = [node for node in graph.nodes() if graph.nodes[node].get('charging_station', False)]

    distanza_minima = float('inf')
    punto_vicino = None

    for station in charging_stations:
        start_dist = h.euclidean_distance(start, station, graph)
        goal_dist = h.euclidean_distance(goal, station, graph)

        # Verifica se il punto C è all'interno della circonferenza
        if start_dist <= raggio:
            # Verifica se il punto C è il più vicino al perimetro e a B
            if start_dist + goal_dist < distanza_minima:
                distanza_minima = start_dist + goal_dist
                punto_vicino = station

    return punto_vicino

# Funzione principale
def main():
    start_time = time.time()
    # Impostazioni iniziali
    max_battery_capacity = 10   # Imposta la capacità massima della batteria in kWh
    min_battery_at_goal = 20     # Imposta la batteria minima di arrivo in %
    ambient_temperature = 20     # Imposta la temperatura ambientale
    electric_constant = 0.06     # Imposta la costante elettrica
    battery = max_battery_capacity # Imposta la batteria iniziale
    location_point = (37.79, -122.41) # Esempio: San Francisco
    #location_point = (45.5257, 10.2283) # Esempio: Milano
    num_charging_stations = 500 # Numero di stazioni di ricarica
    min_battery_percent = max_battery_capacity * min_battery_at_goal / 100 # Batteria minima in percentuale
    # Genera il grafo e le stazioni di ricarica
    G, charging_stations = generate_osm_graph(location_point, 3000, 'drive', num_charging_stations)
    # Scegli un nodo di partenza e di arrivo casuale
    nodes_list = list(G.nodes())
    start_node = random.choice(nodes_list)
    end_node = random.choice(nodes_list)

    print("tempo inizio ricerca", time.time()-start_time)
    solution = adaptive_search(G, start_node, end_node, min_battery_percent, max_battery_capacity, battery, ambient_temperature, electric_constant)

    print("tempo fine ricerca", time.time()-start_time)
    if solution:
        m = draw_solution_on_map(G, solution, start_node, end_node, charging_stations)
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
