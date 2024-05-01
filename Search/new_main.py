import pygame
import osmnx as ox
import random
import time
import numpy as np
import heuristics as h
from path_finding import PathFinding
from electric_vehicle import ElectricVehicleAStar
from ASTAR import AStar

"""versione 2.0.0 con generazione di grafo da OSM e visualizzazione con pygame"""

# Inizializza Pygame
pygame.init()
screen_width, screen_height = 1000, 800
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Simulazione Mappa Stradale')

# Funzione per generare un grafo da OpenStreetMap
def generate_osm_graph(location, dist, network_type, num_charging_stations): # Genera un grafo da OpenStreetMap
    # Scarica i dati della rete stradale da OSM e costruisci un modello MultiDiGraph
    # G = ox.graph_from_point(location, dist=dist, network_type=network_type) # Scarica i dati della rete stradale da OSM
    G = ox.graph_from_place('Milan, Italy', network_type='drive')  # Scarica i dati della rete stradale da OSM
    # Aggiungi velocità, distanza e tempi di percorrenza agli archi
    G = ox.routing.add_edge_speeds(G) # Aggiungi velocità agli archi in km/h 'speed_kph'
    G = ox.routing.add_edge_travel_times(G) # Aggiungi tempi di percorrenza agli archi in secondi s 'travel_time'
    G = ox.distance.add_edge_lengths(G) # Aggiungi lunghezze degli archi in metri m 'length'

    # Aggiungi stazioni di ricarica casuali se non sono già presenti
    all_nodes = list(G.nodes) # Lista di tutti i nodi
    charging_stations = random.sample(all_nodes, num_charging_stations) # Scegli un numero casuale di stazioni di ricarica
    G = ox.utils_graph.convert.to_digraph(G, weight="travel_time") # Converte MultiDiGraph in DiGraph
    G = G.to_undirected() # Converte in un grafo non diretto
    
    for node in charging_stations: # Imposta le stazioni di ricarica casuali
        G.nodes[node]['charging_station'] = True
    # Trova le coordinate minime e massime per normalizzare le coordinate in base alla finestra di Pygame
    x_values = [G.nodes[node]['x'] for node in G.nodes]
    y_values = [G.nodes[node]['y'] for node in G.nodes]
    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = min(y_values), max(y_values)
    # Imposta l'attributo 'pos' per ogni nodo (necessario per disegnare il grafo)
    for node in G.nodes:
        # Normalizza le coordinate in modo che si adattino alla finestra di Pygame
        x = (G.nodes[node]['x'] - min_x) / (max_x - min_x) * screen_width
        y = (1-(G.nodes[node]['y'] - min_y) / (max_y - min_y)) * screen_height
        G.nodes[node]['pos'] = (int(x), int(y))
    return G

# Disegna il grafo sulla finestra di Pygame
def draw_graph(graph, start_node, end_node, screen): # Disegna il grafo sulla finestra di Pygame
    for edge in graph.edges(): # Disegna gli archi
        pygame.draw.line(screen, (200, 200, 200), graph.nodes[edge[0]]['pos'], graph.nodes[edge[1]]['pos'], 2)
    for node in graph.nodes(): # Disegna i nodi
        pos = graph.nodes[node]['pos']
        if node == start_node:
            color = (255, 0, 0) # Rosso per il punto di partenza    
        elif node == end_node:
            color = (0, 200, 0) # Verde per il punto di arrivo
        elif graph.nodes[node].get('charging_station', False):
            color = (0, 0, 255) # Blu per le stazioni di ricarica
        else:
            color = (200, 200, 0) # Giallo per gli altri nodi
        pygame.draw.circle(screen, color, pos, 5) # Disegna i nodi

# Disegna il percorso trovato sulla finestra di Pygame
def draw_solution(graph, solution, screen):
    for action in solution:
        start_pos = graph.nodes[action[0]]['pos']
        end_pos = graph.nodes[action[1]]['pos']
        pygame.draw.line(screen, (255, 0, 255), start_pos, end_pos, 4) # Disegna il percorso

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

# def find_nearest_charging_station(graph, start, goal, current_position, problem):
#     # Ottieni tutte le stazioni di ricarica
#     charging_stations = [node for node in graph.nodes() if graph.nodes[node].get('charging_station', False)]

#     # Inizializza la stazione di ricarica più vicina e la sua distanza
#     nearest_charging_station = None
#     nearest_distance = float('inf')

#     # Per ogni stazione di ricarica, calcola la distanza dalla posizione corrente
#     for station in charging_stations:
#         # Calcola la distanza utilizzando l'algoritmo di ricerca A*
#         astar = AStar(graph, h.euclidean_distance, view=True)
#         path = astar.solve(PathFinding(graph, current_position, station, [], problem.min_battery_percent))
#         if path is None:
#             continue
#         distance = sum(graph[i][j]['length'] for i, j in zip(path[:-1], path[1:]))

#         # Se la distanza è minore della distanza più vicina e il veicolo può raggiungere la stazione, aggiorna la stazione di ricarica più vicina e la sua distanza
#         if distance < nearest_distance and problem.vehicle.can_reach(distance):
#             nearest_charging_station = station
#             nearest_distance = distance

#     return nearest_charging_station

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
    max_battery_capacity = 5   # Imposta la capacità massima della batteria in kWh
    min_battery_at_goal = 20     # Imposta la batteria minima di arrivo in %
    ambient_temperature = 20     # Imposta la temperatura ambientale
    electric_constant = 0.06     # Costante per il calcolo del consumo energetico
    battery = max_battery_capacity # Capacità iniziale della batteria

    # location_point = (45.89, 10.18)  # Esempio: Darfo Boario Terme
    location_point = (37.79, -122.41) # Esempio: San Francisco
    num_charging_stations = 300 # Numero di stazioni di ricarica
    min_battery_percent = max_battery_capacity * min_battery_at_goal / 100 # Batteria minima in percentuale
    G = generate_osm_graph(location_point, 3000, 'drive', num_charging_stations) # Genera il grafo
    nodes_list = list(G.nodes())
    start_node = random.choice(nodes_list) # Scegli un nodo di partenza casuale
    print("start_node", start_node)
    end_node = random.choice(nodes_list) # Scegli un nodo di arrivo casuale
    print("end_node", end_node)

    print("tempo generazione grafo", time.time()-start_time)

    # Inizializza l'algoritmo di ricerca
    
    # distance = sum(G[i][j]['length'] for i, j in zip(solution[:-1], solution[1:]))
    # speed = sum(G[i][j]['speed_kph'] for i, j in zip(solution[:-1], solution[1:]))

    # energy_consumed = electric_constant * (distance / 1000) * speed / ambient_temperature

    # if energy_consumed < max_battery_capacity - min_battery_percent:
    #     print("Percorso trovato con", len(solution), "azioni")
    
    print("tempo inizializzazione", time.time()-start_time)

    # Ciclo di gioco
    running = True
    instructions_executed = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if not instructions_executed:
            screen.fill((0, 0, 0))
            draw_graph(G, start_node, end_node, screen)
            pygame.display.flip()
            # Aggiorna la visualizzazione per ogni nodo espanso
            print("tempo inizio ricerca", time.time()-start_time)
            solution = adaptive_search(G, start_node, end_node, min_battery_percent, max_battery_capacity, battery, ambient_temperature, electric_constant)

            print("tempo fine ricerca", time.time()-start_time)
            if solution:
                draw_solution(G, solution, screen)
            else:    
                print("Percorso non trovato")
                draw_solution(G, solution, screen)
            pygame.display.flip()
            instructions_executed = True
    pygame.quit()
    print("Soluzione:", solution)
    print("Percorso trovato con", len(solution), "azioni")
    print("Fine simulazione")
    # for node in G.nodes():
    #     print(node, G.nodes[node])
    
if __name__ == "__main__":
    main()
