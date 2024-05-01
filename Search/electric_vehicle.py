import osmnx as ox
from ASTAR import AStar, AstarNode
from queue import PriorityQueue

class ElectricVehicleNode(AstarNode): # Nodo per la ricerca A* con veicolo elettrico
    def __init__(self, state, parent=None, action=None, g=0, h=0, battery=100):
        super().__init__(state, parent, action, g)
        self.battery = battery
        self.h = h

    def __lt__(self, other): # Confronta due nodi
        return (self.g + self.h) < (other.g + other.h)

class ElectricVehicleAStar(AStar):
    def __init__(self, graph, heuristic, view=False, battery_capacity=100, min_battery=20, temperature=20):
        super().__init__(heuristic, view)
        self.graph = graph
        self.battery_capacity = battery_capacity
        self.min_battery = min_battery
        self.temperature = temperature
        self.charging_power = 22  # Potenza di ricarica in kW
        
    def solve(self, problem):
        # reached = {}
        reached = set()
        frontier = PriorityQueue()
        frontier.put(ElectricVehicleNode(problem.init, h=self.heuristic(problem.init, problem.goal), battery=self.battery_capacity))
        # reached[(problem.init, self.battery_capacity)] = 0 # Dizionario degli stati raggiunti
        reached.add((problem.init, self.battery_capacity))

        self.reset_expanded()
        while not frontier.empty():
            n = frontier.get()
            if problem.isGoal(n.state, n.battery):
                return self.extract_solution(n)
            for action, s, cost, time in problem.getSuccessors(n.state):
                new_battery = n.battery - (cost / self.temperature)
                if new_battery > 0:
                    charging_time = 0
                    if problem.is_charging_station(n.state):
                        desired_battery_level = self.calculate_desired_battery_level(n.state, problem)
                        if desired_battery_level > n.battery:
                            charging_time = (desired_battery_level - n.battery) / self.charging_power
                            new_battery = desired_battery_level
                    new_state = (s, new_battery)
                    new_g = n.g + (time / 3600) + charging_time
                    if new_state not in reached:# or new_g < reached[new_state]:
                        self.update_expanded(s)
                        # reached[new_state] = new_g
                        reached.add(new_state)
                        new_h = self.heuristic(s, problem.goal, self.graph)
                        frontier.put(ElectricVehicleNode(s, n, action, new_g, new_h, new_battery))
        return None
    
    def calculate_desired_battery_level(self, current_state, problem):
        # Calcola il percorso più breve dalla stazione di ricarica corrente all'obiettivo
        shortest_path = ox.routing.shortest_path(self.graph, current_state, problem.goal, weight='length', cpus=1)
        # Trova la prossima stazione di ricarica lungo il percorso più breve
        next_charging_station = next((node for node in shortest_path if problem.is_charging_station(node)), problem.goal)
        
        # Calcola il costo del viaggio dalla stazione di ricarica corrente alla prossima stazione di ricarica
        travel_length = sum(self.graph[i][j]['length'] for i, j in zip(shortest_path, shortest_path[1:]) if j != next_charging_station)
        travel_speed = sum(self.graph[i][j]['speed_kph'] for i, j in zip(shortest_path, shortest_path[1:]) if j != next_charging_station)

        # Calcola il livello di carica necessario per raggiungere la prossima stazione di ricarica
        energy_consume = 0.06 * travel_length / 1000 * travel_speed / self.temperature
        if next_charging_station == problem.goal:
            return self.min_battery + energy_consume
        return energy_consume

    def calculate_desired_battery_level(self, current_state, problem):
        # Calcola il percorso più breve dalla stazione di ricarica corrente all'obiettivo
        shortest_path = ox.routing.shortest_path(self.graph, current_state, problem.goal, weight='length', cpus=1)
    
        # Trova la prossima stazione di ricarica lungo il percorso più breve
        next_charging_station = next((node for node in shortest_path if problem.is_charging_station(node)), problem.goal)
    
        # Calcola il costo del viaggio dalla stazione di ricarica corrente alla prossima stazione di ricarica
        travel_length = sum(self.graph[i][j]['length'] for i, j in zip(shortest_path, shortest_path[1:]) if j != next_charging_station)
        travel_speed = sum(self.graph[i][j]['speed_kph'] for i, j in zip(shortest_path, shortest_path[1:]) if j != next_charging_station)

        # Calcola il livello di carica necessario per raggiungere la prossima stazione di ricarica
        energy_consume = 0.06 * travel_length / 1000 * travel_speed / self.temperature
    
        # Se la batteria non è sufficiente per raggiungere la destinazione, trova la stazione di ricarica più vicina lungo il percorso
        if energy_consume > self.battery:
            nearest_charging_station = self.find_nearest_charging_station(current_state, problem)
            if nearest_charging_station is not None:
                next_charging_station = nearest_charging_station
                shortest_path = ox.routing.shortest_path(self.graph, current_state, next_charging_station, weight='length', cpus=1)
                travel_length = sum(self.graph[i][j]['length'] for i, j in zip(shortest_path, shortest_path[1:]))
                travel_speed = sum(self.graph[i][j]['speed_kph'] for i, j in zip(shortest_path, shortest_path[1:]))
                energy_consume = 0.06 * travel_length / 1000 * travel_speed / self.temperature

        if next_charging_station == problem.goal:
            return self.min_battery + energy_consume
        return energy_consume
    