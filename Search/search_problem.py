class SearchProblem: # Problema di ricerca generico
    def __init__(self, init, goal, graph, charging_stations, min_battery_at_goal):
        self.init = init
        self.goal = goal
        self.graph = graph
        self.charging_stations = charging_stations
        self.min_battery_at_goal = min_battery_at_goal

    # def getSuccessors(self, state):
    #     electric_constant = 0.05
    #     successors = set()
    #     for neighbor, edge_data in self.graph[state].items():
    #         action = (state, neighbor)
    #         distance = edge_data[list(edge_data.keys())[0]]['length']
    #         speed = edge_data[list(edge_data.keys())[0]].get('speed_kph', 50)  # Velocità in km/h
    #         energy_consumed = electric_constant * (distance / 1000) * speed # k * d(km) * v(km/h) = kWh * °C
    #         time = edge_data[list(edge_data.keys())[0]]['travel_time']
    #         successors.add((action, neighbor, energy_consumed, time))
    #     return successors

    def getSuccessors(self, state):
        # electric_constant = 0.05
        electric_constant = 0.5
        successors = set()
        for neighbor, edge_data in self.graph[state].items():
            action = (state, neighbor)
            distance = edge_data['length']
            speed = edge_data.get('speed_kph', 50)  # Velocità in km/h
            energy_consumed = electric_constant * (distance / 1000) * speed # k * d(km) * v(km/h) = kWh * °C
            time = edge_data['travel_time']
            successors.add((action, neighbor, energy_consumed, time))
        return successors

    def isGoal(self, state, battery_level): # Verifica se uno stato è l'obiettivo
        return state == self.goal and battery_level >= self.min_battery_at_goal

    def is_charging_station(self, state): # Verifica se uno stato è una stazione di ricarica
        return state in self.charging_stations
