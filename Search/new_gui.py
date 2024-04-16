import networkx as nx
import pygame
import json
import random

# Carica il grafo da un file .json
def load_graph_from_json(file_name):
    with open(file_name, 'r') as f:
        data = json.load(f)
    return nx.node_link_graph(data)

# Inizializza Pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))

# Carica il grafo
graph = load_graph_from_json('graph.json')

# Funzione per disegnare il grafo
def draw_graph(graph, screen):
    for node in graph.nodes():
        x, y = random.randint(50, 750), random.randint(50, 550)  # Posizioni casuali, da migliorare
        if 'charging_station' in graph.nodes[node]:
            color = (0, 255, 0)  # Verde per le stazioni di ricarica
        else:
            color = (0, 0, 255)  # Blu per i nodi normali
        pygame.draw.circle(screen, color, (x, y), 20)
    # Aggiungi qui il codice per disegnare gli archi

# Loop principale di Pygame
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    screen.fill((255, 255, 255))  # Sfondo bianco
    draw_graph(graph, screen)
    pygame.display.flip()

pygame.quit()