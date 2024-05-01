import pygame
import osmnx as ox
import networkx as nx
import random
from path_finding import PathFinding
from electric_vehicle import ElectricVehicleAStar
from heuristics import euclidean_distance

# Inizializza Pygame
pygame.init()
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Simulazione Mappa Stradale')

# Configura OSMnx per utilizzare la cache e ridurre il tempo di download
ox.settings.use_cache = True

# Funzione per generare un grafo da OpenStreetMap
def generate_osm_graph(location_point, dist, network_type, num_charging_stations):
    # Scarica i dati della rete stradale da OSM e costruisci un modello MultiDiGraph
    G = ox.graph_from_point(location_point, dist=dist, network_type=network_type)

    # Aggiungi velocità e tempi di percorrenza agli archi
    G = ox.routing.add_edge_speeds(G)
    G = ox.routing.add_edge_travel_times(G)

    # Aggiungi stazioni di ricarica casuali se non sono già presenti
    all_nodes = list(G.nodes)
    charging_stations = random.sample(all_nodes, num_charging_stations)
    G = ox.utils_graph.convert.to_digraph(G, weight="travel_time") # Converte MultiDiGraph in DiGraph
    
    for node in charging_stations:
        G.nodes[node]['charging_station'] = True

    # Trova le coordinate minime e massime
    x_values = [G.nodes[node]['x'] for node in G.nodes]
    y_values = [G.nodes[node]['y'] for node in G.nodes]
    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = min(y_values), max(y_values)

    # Imposta l'attributo 'pos' per ogni nodo (necessario per disegnare il grafo)
    for node in G.nodes:
        # Normalizza le coordinate in modo che si adattino alla finestra di Pygame
        x = (G.nodes[node]['x'] - min_x) / (max_x - min_x) * screen_width
        y = (G.nodes[node]['y'] - min_y) / (max_y - min_y) * screen_height
        G.nodes[node]['pos'] = (int(x), int(y))

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
        elif graph.nodes[node].get('charging_station', False):
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

def main():
    # Impostazioni iniziali
    max_battery_capacity = 10000   # Imposta la capacità massima della batteria
    min_battery_at_goal = 20     # Imposta la batteria minima di arrivo
    ambient_temperature = 20     # Imposta la temperatura ambientale

    location_point = (37.79, -122.41)  # Esempio: San Francisco
    num_charging_stations = 40
    G = generate_osm_graph(location_point, 750, 'drive', num_charging_stations) # Genera il grafo
    start_node = random.choice(list(G.nodes())) # Scegli un nodo di partenza casuale
    end_node = random.choice(list(G.nodes())) # Scegli un nodo di arrivo casuale

    # Debug: Stampa il numero di nodi e archi nel grafo
    print(f"Number of nodes: {G.number_of_nodes()}")
    print(f"Number of edges: {G.number_of_edges()}")

    # Debug: Verifica che il nodo di partenza e il nodo di arrivo non siano lo stesso
    if start_node == end_node:
        print("Start node and end node are the same. Please choose different nodes.")
        return

    # Debug: Verifica che le posizioni dei nodi siano nel formato corretto e nell'intervallo delle dimensioni della finestra
    for node in G.nodes():
        pos = G.nodes[node]['pos']
        if not isinstance(pos, tuple) or len(pos) != 2:
            print(f"Node {node} has an invalid position: {pos}. Position should be a tuple of two integers.")
            return
        if pos[0] < 0 or pos[0] > screen_width or pos[1] < 0 or pos[1] > screen_height:
            print(f"Node {node} has a position out of screen bounds: {pos}. Position should be within (0, 0) and ({screen_width}, {screen_height}).")
            return

    # Inizializza l'algoritmo di ricerca
    problem = PathFinding(G, start_node, end_node, [node for node in G.nodes() if G.nodes[node].get('charging_station', False)], min_battery_at_goal)
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
            draw_solution(G, solution, screen)
        pygame.display.flip()
    pygame.quit()
    print(f"Solution: {solution}")
    print("Fine simulazione")

if __name__ == "__main__":
    main()
