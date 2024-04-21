import pygame
import networkx as nx
import random
import json
from path_finding import PathFinding
from electric_vehicle import ElectricVehicleAStar
from heuristics import euclidean_distance

# Initialize Pygame
pygame.init()
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Simulazione Mappa Stradale')

# Function to generate a connected graph
def generate_connected_graph(num_nodes, num_charging_stations):
    G = nx.connected_watts_strogatz_graph(num_nodes, k=3, p=0.5)
    for node in G.nodes():
        G.nodes[node]['pos'] = (random.randint(0, screen_width - 10), random.randint(0, screen_height - 10))
        G.nodes[node]['charging_station'] = False
    for node in random.sample(list(G.nodes()), num_charging_stations):
        G.nodes[node]['charging_station'] = True
    return G

# Function to draw the graph on the Pygame window
def draw_graph(graph, start_node, end_node, screen):
    for edge in graph.edges():
        pygame.draw.line(screen, (200, 200, 200), graph.nodes[edge[0]]['pos'], graph.nodes[edge[1]]['pos'], 2)
    for node in graph.nodes():
        pos = graph.nodes[node]['pos']
        if node == start_node:
            color = (255, 0, 0)
        elif node == end_node:
            color = (0, 255, 0)
        elif graph.nodes[node]['charging_station']:
            color = (0, 0, 255)  # Blue for charging stations
        else:
            color = (255, 255, 0)
        pygame.draw.circle(screen, color, pos, 5)

# Function to draw the solution path on the Pygame window
def draw_solution(graph, solution, screen):
    for action in solution:
        start_pos = graph.nodes[action[0]]['pos']
        end_pos = graph.nodes[action[1]]['pos']
        pygame.draw.line(screen, (255, 0, 255), start_pos, end_pos, 4)

# Function to import a graph from a JSON file
def import_graph_from_json(file_name):
    with open(file_name, 'r') as json_file:
        graph_data = json.load(json_file)
    return nx.node_link_graph(graph_data)

# Function to export a graph to a JSON file
def export_graph_to_json(graph, file_name):
    graph_data = nx.node_link_data(graph)
    with open(file_name, 'w') as json_file:
        json.dump(graph_data, json_file, indent=4)
    print(f"mappa {file_name}")

# Main function
def main():
    num_nodes = 20
    num_charging_stations = 5
    G = generate_connected_graph(num_nodes, num_charging_stations)
    start_node = random.choice(list(G.nodes()))
    end_node = random.choice(list(G.nodes()))
    problem = PathFinding(G, start_node, end_node, [node for node in G.nodes() if G.nodes[node]['charging_station']])
    astar = ElectricVehicleAStar(G, heuristic=lambda node_a, node_b, graph=G: euclidean_distance(node_a, node_b, graph), view=True)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        screen.fill((0, 0, 0))
        draw_graph(G, start_node, end_node, screen)
        solution = astar.solve(problem)
        if solution:
            draw_solution(G, solution, screen)
        pygame.display.flip()
    pygame.quit()
    print("Fine simulazione")

if __name__ == "__main__":
    main()
