import pygame
import networkx as nx
import random
import json
from path_finding import PathFinding
from electric_vehicle import ElectricVehicleAStar
from heuristics import euclidean_distance
import osmnx as ox
"""versione 1.0.0 con generazione di grafo casuale e visualizzazione con pygame"""
# Inizializza Pygame
pygame.init()
screen_width, screen_height = 800, 600 # Dimensioni della finestra
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Simulazione Mappa Stradale')

# Genera un grafo connesso con percorsi alternativi
def generate_connected_graph(num_nodes, num_charging_stations): # Genera un grafo connesso
    G = nx.connected_watts_strogatz_graph(num_nodes, k=3, p=0.5)  # decidere valori di k e p
    for node in G.nodes():  # Posizioni casuali
        G.nodes[node]['pos'] = (random.randint(0, screen_width - 10), random.randint(0, screen_height - 10))
        G.nodes[node]['charging_station'] = False  # Nessuna stazione di ricarica
    for node in random.sample(list(G.nodes()), num_charging_stations):  # Stazioni di ricarica casuali
        G.nodes[node]['charging_station'] = True  # Aggiungi stazioni di ricarica
    return G

# Disegna il grafo sulla finestra di Pygame
def draw_graph(graph, start_node, end_node, screen):
    for edge in graph.edges(): # Disegna gli archi
        pygame.draw.line(screen, (200, 200, 200), graph.nodes[edge[0]]['pos'], graph.nodes[edge[1]]['pos'], 2)

    for node in graph.nodes():
        pos = graph.nodes[node]['pos']
        if node == start_node:
            color = (255, 0, 0) # Rosso per il punto di partenza    
        elif node == end_node:
            color = (0, 255, 0) # Verde per il punto di arrivo
        elif graph.nodes[node]['charging_station']:
            color = (0, 0, 255) # Blu per le stazioni di ricarica
        else:
            color = (255, 255, 0) # Giallo per gli altri nodi
        pygame.draw.circle(screen, color, pos, 5) # Disegna i nodi

# Disegna il percorso trovato sulla finestra di Pygame
def draw_solution(graph, solution, screen):
    for action in solution:
        start_pos = graph.nodes[action[0]]['pos']
        end_pos = graph.nodes[action[1]]['pos']
        pygame.draw.line(screen, (255, 0, 255), start_pos, end_pos, 4)

#DA IMPLEMENTARE L'UTILIZZO
def import_graph_from_json(file_name):
    # Leggi i dati JSON dal file
    with open(file_name, 'r') as json_file:
        graph_data = json.load(json_file)
    
    # Converti i dati del dizionario in un grafo
    graph = nx.node_link_graph(graph_data)
    
    return graph

#DA IMPLEMENTARE L'UTILIZZO
def export_graph_to_json(graph, file_name):
    # Converti il grafo in un formato di dati dizionario
    graph_data = nx.node_link_data(graph)
    
    # Scrivi i dati del dizionario in un file JSON
    with open(file_name, 'w') as json_file:
        json.dump(graph_data, json_file, indent=4)
    
    print(f"La mappa è stata esportata come {file_name}")


def main(): # Funzione principale
    #initial_battery_level = 100  # Imposta il livello iniziale della batteria # DA IMPLEMENTARE
    max_battery_capacity = 100   # Imposta la capacità massima della batteria
    min_battery_at_goal = 20     # Imposta la batteria minima di arrivo
    ambient_temperature = 20     # Imposta la temperatura ambientale

    num_nodes = 20
    num_charging_stations = 5
    G = generate_connected_graph(num_nodes, num_charging_stations) # Genera il grafo
    start_node = random.choice(list(G.nodes())) # Scegli un nodo di partenza casuale
    end_node = random.choice(list(G.nodes())) # Scegli un nodo di arrivo casuale

    # # Utilizza OSMnx per ottenere i dati della mappa # DA IMPLEMENTARE
    # location_point = (37.79, -122.41)  # Esempio: San Francisco
    # G = ox.graph_from_point(location_point, dist=750, network_type='drive')
    # G = ox.speed.add_edge_speeds(G)
    # G = ox.speed.add_edge_travel_times(G)

    # Inizializza l'algoritmo di ricerca
    problem = PathFinding(G, start_node, end_node, [node for node in G.nodes() if G.nodes[node]['charging_station']], min_battery_at_goal)
    astar = ElectricVehicleAStar(G, heuristic=lambda node_a, node_b, graph=G: euclidean_distance(node_a, node_b, graph), view=True, battery_capacity=max_battery_capacity, min_battery=min_battery_at_goal, temperature=ambient_temperature)

    # Ciclo di gioco
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 0))
        draw_graph(G, start_node, end_node, screen)

        # Aggiorna la visualizzazione per ogni nodo espanso
        solution = astar.solve(problem)
        if solution:
            draw_solution(G, solution, screen) # Disegna il percorso trovato

        pygame.display.flip()

    pygame.quit()
    print("Fine simulazione")

if __name__ == "__main__":
    main()


# def adaptive_search(self, graph, start, goal, ambient_temperature, path=[]):
#         # Inizializza l'algoritmo di ricerca
#         problem = PathFinding(graph, start, goal)
#         # Inizializza l'algoritmo di ricerca A*
#         astar = AStar(graph, h.euclidean_distance, view=True)
#         solution = astar.solve(problem)
#         # print("soluzione", solution, "dim", len(solution))
#         if solution is None:
#             print("Percorso tot non trovato")
#             return None
    
#         # Calcola la distanza, la velocità e l'energia consumata
#         distance = speed = energy_consumed = time = 0
#         for i, j in solution:
#             distance = graph.edges[i, j].get('length', 10)
#             speed = graph.edges[i, j].get('speed_kph', 50)
#             energy_consumed += self.electric_constant * (distance / 1000) * speed / ambient_temperature
#             time += graph.edges[i, j].get('travel_time', 10)

#         # Se l'energia consumata è inferiore alla capacità massima della batteria, restituisci il percorso
#         if energy_consumed < self.battery - self.min_battery:
#             # Aggiungi il percorso alla soluzione
#             path += solution # se il nodo iniziale è uguale sostituisci, altrimenti cerca il nodo iniziale di soluzion in path e sostituisci da li
#             self.travel_time += time
#             self.battery -= energy_consumed
#             return path

#         charging_station_start, solution, energy_consumed, time = self.nearest_charging_station(graph, start, goal, solution, ambient_temperature)
#         if charging_station_start is None:
#             print("Stazione di ricarica non trovata")
#             return None
#         if solution is None:
#             print("Percorso stazione non trovato")
#             return None
            
#         # Aggiungi il percorso alla soluzione
#         path += solution # se il nodo iniziale è uguale sostituisci, altrimenti cerca il nodo iniziale di soluzion in path e sostituisci da li
#         self.travel_time += time
#         self.battery -= energy_consumed

#         distance = h.euclidean_distance(charging_station_start, goal, graph)
#         energy_needed = (self.electric_constant * distance * 60 / ambient_temperature) * 1.2
#         if energy_needed >= self.battery_capacity or energy_needed + self.min_battery >= self.battery_capacity or energy_needed + self.battery >= self.battery_capacity:
#             recharge_needed = self.battery_capacity - self.battery
#         else:
#             recharge_needed = energy_needed
#             #recharge_needed = self.battery_capacity - self.battery
#         self.energy_recharged.append(recharge_needed)
#         self.travel_time += (recharge_needed) / 22 * 3600
#         self.battery = recharge_needed   
#         self.recharge += 1
#         graph.nodes[charging_station_start]['charging_station'] = False
#         print("qua ci arrivo")
#         return self.adaptive_search(graph, charging_station_start, goal, ambient_temperature, path)