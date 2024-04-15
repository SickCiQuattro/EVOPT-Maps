def manhattan(start, goal) -> int:
    x_distance = abs(start[0] - goal[0])
    y_distance = abs(start[1] - goal[1])
    return x_distance + y_distance

def blind(start, goal) -> int:
    return 0