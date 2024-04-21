class SearchProblem: # Problema di ricerca generico
    def __init__(self, init, goal, graph, charging_stations, min_battery_at_goal):
        self.init = init
        self.goal = goal
        self.graph = graph
        self.charging_stations = charging_stations
        self.min_battery_at_goal = min_battery_at_goal

    def getSuccessors(self, state): # Ritorna i successori di uno stato
        successors = set() # Insieme dei successori
        for neighbor in self.graph.neighbors(state): # Per ogni vicino dello stato
            action = (state, neighbor)
            # Per MultiGraph, potrebbe essere necessario specificare la chiave per l'arco
            # Se il grafo non è un MultiGraph, usa il seguente codice:
            distance = self.graph.edges[state, neighbor].get('length', 1) # Calcola la distanza
            # Se il grafo è un MultiGraph, usa il seguente codice:
            # for key in self.graph[state][neighbor]:
            #     distance = self.graph[state][neighbor][key].get('length', 1)
            successors.add((action, neighbor, distance))
        return successors

    def isGoal(self, state, battery_level): # Verifica se uno stato è l'obiettivo
        return state == self.goal and battery_level >= self.min_battery_at_goal

    def is_charging_station(self, state): # Verifica se uno stato è una stazione di ricarica
        return state in self.charging_stations
