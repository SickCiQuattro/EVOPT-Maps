import pygame
import osmnx as ox
import random
import time
import electric_vehicle as ev
import heuristics as h
from path_finding import PathFinding
from Search.fallimento.electricASTAR import ElectricVehicleAStar

"""versione 2.0.0 con generazione di grafo da OSM e visualizzazione con pygame"""

# Inizializza Pygame
pygame.init()
screen_width, screen_height = 1000, 800
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Simulazione Mappa Stradale')

# Funzione per generare un grafo da OpenStreetMap
def generate_osm_graph(location, dist, network_type, num_charging_stations):
    # Genera un grafo da OpenStreetMap
    G = ox.graph_from_point(location, dist=dist, network_type=network_type, simplify=False)
    # G = ox.graph_from_place('Brescia', network_type='drive')  # Scarica i dati della rete stradale da OSM
    G = ox.routing.add_edge_speeds(G) # Aggiungi velocità agli archi in km/h 'speed_kph'
    G = ox.routing.add_edge_travel_times(G) # Aggiungi tempi di percorrenza agli archi in secondi s 'travel_time'
    G = ox.distance.add_edge_lengths(G) # Aggiungi lunghezze degli archi in metri m 'length'
    # Aggiungi stazioni di ricarica casuali
    all_nodes = list(G.nodes)
    # Scegli un numero casuale di stazioni di ricarica
    charging_stations = random.sample(all_nodes, num_charging_stations)
    G = ox.utils_graph.convert.to_digraph(G, weight="travel_time") # Converte MultiDiGraph in DiGraph
    #G = G.to_undirected() # Converte in un grafo non diretto
    
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
        y = (1 - (G.nodes[node]['y'] - min_y) / (max_y - min_y)) * screen_height
        G.nodes[node]['pos'] = (int(x), int(y))
    return G, charging_stations

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

# Funzione principale
def main():
    start_time = time.time()
    # Impostazioni iniziali
    battery_capacity = 9   # Imposta la capacità massima della batteria in kWh
    battery_at_goal_percent = 30     # Imposta la batteria minima di arrivo in %
    # electric_constant = 0.05     # Imposta la costante elettrica
    electric_constant = 0.4     # Imposta la costante elettrica
    battery = battery_capacity # Imposta la batteria iniziale
    battery_at_goal = battery_capacity * battery_at_goal_percent / 100 # Batteria minima in percentuale
    electric_vehicle = ev.ElectricVehicle(battery_capacity, battery, battery_at_goal, electric_constant)

    ambient_temperature = 20     # Imposta la temperatura ambientale
    location_point = (37.79, -122.41) # Esempio: San Francisco
    #location_point = (45.5257, 10.2283) # Esempio: Milano
    num_charging_stations = 1000 # Numero di stazioni di ricarica
    # Genera il grafo e le stazioni di ricarica
    G, charging_stations = generate_osm_graph(location_point, 2000, 'drive', num_charging_stations) # Genera il grafo
    nodes_list = list(G.nodes())
    start_node = random.choice(nodes_list) # Scegli un nodo di partenza casuale
    print("start_node", start_node)
    end_node = random.choice(nodes_list) # Scegli un nodo di arrivo casuale
    print("end_node", end_node)

    problem = PathFinding(G, start_node, end_node)
    # Inizializza l'algoritmo di ricerca A*
    astar = ElectricVehicleAStar(G, heuristic=lambda node_a, node_b, G: h.shortest_destination(node_a, node_b, G), view=True, vehicle = electric_vehicle, temperature = ambient_temperature, charging_stations = charging_stations)

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
            solution = astar.solve(problem)
            print("tempo fine ricerca", time.time()-start_time)
            if solution:
                draw_solution(G, solution, screen)
            else:    
                print("Percorso non trovato")
                draw_solution(G, solution, screen)
            pygame.display.flip()
            instructions_executed = True
    pygame.quit()
    
    print("battery", electric_vehicle.battery, "energia ricaricata", electric_vehicle.energy_recharged, "tempo in ore", electric_vehicle.travel_time/3600)
    print("Macchina ricaricata ", electric_vehicle.recharge, " volte")
    print("Soluzione:", solution)
    print("Percorso trovato con", len(solution), "azioni")
    print("Fine simulazione")
    
if __name__ == "__main__":
    main()
