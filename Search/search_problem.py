class SearchProblem: # Problema di ricerca generico
    def __init__(self, init, goal, graph, charging_stations, min_battery_at_goal):
        self.init = init
        self.goal = goal
        self.graph = graph
        self.charging_stations = charging_stations
        self.min_battery_at_goal = min_battery_at_goal

    def __init__(self, init, goal, graph):
        self.init = init
        self.goal = goal
        self.graph = graph

    def getSuccessors(self, state): #DiGraph
        electric_constant = 0.06
        # electric_constant = 1
        successors = set()
        for neighbor in self.graph.neighbors(state):
            action = (state, neighbor)
            distance = self.graph.edges[state, neighbor].get('length', 100) # Distanza in metri
            speed = self.graph.edges[state, neighbor].get('speed_kph', 50)  # Velocità in km/h
            energy_consumed = electric_constant * (distance / 1000) * speed # k * d(km) * v(km/h) = kWh * °C

            time = self.graph.edges[state, neighbor].get('travel_time', 10) # Tempo di percorrenza in secondi
            successors.add((action, neighbor, energy_consumed, time))
        return successors

    def isGoal(self, state, battery_level): # Verifica se uno stato è l'obiettivo
        return state == self.goal and battery_level >= self.min_battery_at_goal
    
    def isGoal(self, state): # Verifica se uno stato è l'obiettivo
        return state == self.goal

    def is_charging_station(self, state): # Verifica se uno stato è una stazione di ricarica
        return state in self.charging_stations
