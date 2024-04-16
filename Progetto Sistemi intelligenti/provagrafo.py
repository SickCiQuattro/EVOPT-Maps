import networkx as nx
import matplotlib.pyplot as plt

def create_graph(nodes):
    G = nx.DiGraph()  # Crea un grafo diretto

    # Aggiungi nodi al grafo
    G.add_node("start", color='green')
    G.add_node("end", color='red')

    for path, n in enumerate(nodes):
        for i in range(n):
            G.add_node(f"node_{i}_path{path + 1}")

        # Aggiungi bordi al grafo con pesi
        G.add_edge("start", f"node_0_path{path + 1}", weight=path + 1)
        for i in range(n - 1):
            G.add_edge(f"node_{i}_path{path + 1}", f"node_{i + 1}_path{path + 1}", weight=path + 1)
        G.add_edge(f"node_{n - 1}_path{path + 1}", "end", weight=path + 1)

    return G

def draw_graph(G):
    pos = nx.spring_layout(G)
    colors = []
    labels = {}  # Crea un dizionario per le etichette dei nodi
    for node in G.nodes(data=True):
        try:
            colors.append(node[1]['color'])
        except KeyError:
            colors.append('blue')  # colore di default per i nodi senza un attributo 'color'
        if node[0] in ['start', 'end']:  # Se il nodo è 'start' o 'end'
            labels[node[0]] = node[0]  # Aggiungi l'etichetta al dizionario
    nx.draw(G, pos, labels=labels, node_color=colors)  # Passa il dizionario delle etichette alla funzione draw
    plt.show()

def find_all_paths(G, start, end):
    paths = list(nx.all_simple_paths(G, start, end))
    return paths

G = create_graph([3, 2, 2])
paths = find_all_paths(G, "start", "end")
for path in paths:
    print(path)
draw_graph(G)