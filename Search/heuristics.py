import math

def manhattan(start, goal) -> int:
    x_distance = abs(start[0] - goal[0])
    y_distance = abs(start[1] - goal[1])
    return x_distance + y_distance

def euclidean_distance(node_a, node_b):
    x1, y1 = node_a
    x2, y2 = node_b
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def blind(start, goal) -> int:
    return 0