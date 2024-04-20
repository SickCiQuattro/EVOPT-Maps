import math

def euclidean_distance(node_a, node_b, graph): # distanza euclidea tra due nodi
    x1, y1 = graph.nodes[node_a]['pos']
    x2, y2 = graph.nodes[node_b]['pos']
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def blind(start, goal) -> int:
    return 0