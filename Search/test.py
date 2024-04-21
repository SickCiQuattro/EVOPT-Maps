import json
import math
import networkx as nx
import pygame
import random
from queue import PriorityQueue

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
TEMPERATURE_EFFECT = 0.1  # Percentage decrease in battery efficiency per degree below 20°C

# Helper functions
def euclidean_distance(node_a, node_b, graph):
    x1, y1 = graph.nodes[node_a]['pos']
    x2, y2 = graph.nodes[node_b]['pos']
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def temperature_effect(temperature):
    """Calculate the effect of temperature on battery efficiency."""
    if temperature < 20:
        return 1 - ((20 - temperature) * TEMPERATURE_EFFECT)
    return 1

# GUI functions
def draw_graph(graph, start_node, end_node, screen):
    # Draw edges
    for edge in graph.edges():
        pygame.draw.line(screen, (200, 200, 200), graph.nodes[edge[0]]['pos'], graph.nodes[edge[1]]['pos'], 2)
    # Draw nodes
    for node in graph.nodes():
        pos = graph.nodes[node]['pos']
        color = (255, 0, 0) if node == start_node else (0, 255, 0) if node == end_node else (255, 255, 0)
        pygame.draw.circle(screen, color, pos, 5)

def draw_solution(graph, solution, screen):
    for action in solution:
        start_pos = graph.nodes[action[0]]['pos']
        end_pos = graph.nodes[action[1]]['pos']
        pygame.draw.line(screen, (255, 0, 255), start_pos, end_pos, 4)

# ElectricVehicleNode class
class ElectricVehicleNode:
    def __init__(self, state, parent=None, action=None, g=0, h=0, battery=100, temperature=20):
        self.state = state
        self.parent = parent
        self.action = action
        self.g = g
        self.h = h
        self.battery = battery
        self.temperature = temperature

    def __lt__(self, other):
        return (self.g + self.h, self.battery) < (other.g + other.h, other.battery)

# ElectricVehicleAStar class
class ElectricVehicleAStar:
    def __init__(self, graph, heuristic=euclidean_distance, view=False, battery_capacity=100, min_battery=0, temperature=20):
        self.graph = graph
        self.heuristic = heuristic
        self.view = view
        self.battery_capacity = battery_capacity
        self.min_battery = min_battery
        self.temperature = temperature

    def solve(self, start, goal):
        reached = set()
        frontier = PriorityQueue()
        start_node = ElectricVehicleNode(start, battery=self.battery_capacity, temperature=self.temperature)
        frontier.put(start_node)
        reached.add((start, self.battery_capacity))

        while not frontier.empty():
            current_node = frontier.get()
            if current_node.state == goal and current_node.battery >= self.min_battery:
                return self.extract_solution(current_node)
            for neighbor in self.graph.neighbors(current_node.state):
                distance = euclidean_distance(current_node.state, neighbor, self.graph)
                battery_consumption = distance * temperature_effect(current_node.temperature)
                new_battery = current_node.battery - battery_consumption
                if new_battery > 0 and (neighbor, new_battery) not in reached:
                    reached.add((neighbor, new_battery))
                    new_g = current_node.g + distance
                    new_h = self.heuristic(neighbor, goal, self.graph)
                    new_node = ElectricVehicleNode(neighbor, current_node, (current_node.state, neighbor), new_g, new_h, new_battery, self.temperature)
                    frontier.put(new_node)

        return None

    def extract_solution(self, node):
        solution = []
        while node.parent is not None:
            solution.insert(0, node.action)
            node = node.parent
        return solution

# Main function
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Electric Vehicle Path Finding')

    # Generate graph
    G = nx.connected_watts_strogatz_graph(20, k=3, p=0.5)
    for node in G.nodes():
        G.nodes[node]['pos'] = (random.randint(0, SCREEN_WIDTH - 10), random.randint(0, SCREEN_HEIGHT - 10))

    # Set start and goal
    start_node = random.choice(list(G.nodes()))
    end_node = random.choice(list(G.nodes()))

    # Initialize A* algorithm
    astar = ElectricVehicleAStar(G, battery_capacity=100, min_battery=20, temperature=10)  # Imposta qui la temperatura e la batteria minima

    # Game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 0))
        draw_graph(G, start_node, end_node, screen)

        # Update visualization for each expanded node
        solution = astar.solve(start_node, end_node)
        if solution:
            draw_solution(G, solution, screen)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
