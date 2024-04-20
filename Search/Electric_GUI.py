import pygame
import networkx as nx
import random
import json
from path_finding import PathFinding
from electric_vehicle import ElectricVehicleAStar
from heuristics import euclidean_distance

# Inizializza Pygame
pygame.init()
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Simulazione Mappa Stradale')

# Genera un grafo connesso con percorsi alternativi
def generate_connected_graph(num_nodes, num_charging_stations):
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
    num_nodes = 20
    num_charging_stations = 5
    G = generate_connected_graph(num_nodes, num_charging_stations) # Genera il grafo
    start_node = random.choice(list(G.nodes())) # Scegli un nodo di partenza casuale
    end_node = random.choice(list(G.nodes())) # Scegli un nodo di arrivo casuale

    # Inizializza l'algoritmo di ricerca
    problem = PathFinding(G, start_node, end_node, [node for node in G.nodes() if G.nodes[node]['charging_station']])
    astar = ElectricVehicleAStar(G, heuristic=lambda node_a, node_b, graph=G: euclidean_distance(node_a, node_b, graph), view=True)

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
