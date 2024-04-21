from search_problem import SearchProblem

class PathFinding(SearchProblem): # Problema di ricerca per il percorso
    def __init__(self, graph, init, goal, charging_stations, min_battery_at_goal):
        super().__init__(init, goal, graph, charging_stations, min_battery_at_goal)
