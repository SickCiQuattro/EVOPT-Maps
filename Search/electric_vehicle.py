import osmnx as ox
import heuristics as h
from ASTAR import AStar, AstarNode
from queue import PriorityQueue
from path_finding import PathFinding

class ElectricVehicle:
    def __init__(self, battery_capacity = 100, battery = 100, min_battery = 20, electric_constant = 0.06, energy_recharged = [], travel_time = 0):
        self.battery_capacity = battery_capacity
        self.battery = battery
        self.min_battery = min_battery
        self.electric_constant = electric_constant
        self.recharge = 0
        self.energy_recharged = energy_recharged
        self.travel_time = travel_time

    def adaptive_search(self, graph, start, goal, ambient_temperature, path=[]):
        # Inizializza l'algoritmo di ricerca
        problem = PathFinding(graph, start, goal)
        # Inizializza l'algoritmo di ricerca A*
        astar = AStar(graph, h.euclidean_distance, view=True)
        solution = astar.solve(problem)
        # print("soluzione", solution, "dim", len(solution))
        if solution is None:
            return None
    
        # Calcola la distanza, la velocità e l'energia consumata
        distance = speed = energy_consumed = time = 0
        for i, j in solution:
            distance = graph.edges[i, j].get('length', 10)
            speed = graph.edges[i, j].get('speed_kph', 50)
            energy_consumed += self.electric_constant * (distance / 1000) * speed / ambient_temperature
            time += graph.edges[i, j].get('travel_time', 10)

        # Se l'energia consumata è inferiore alla capacità massima della batteria, restituisci il percorso
        if energy_consumed < self.battery - self.min_battery:
            # Aggiungi il percorso alla soluzione
            path += solution # se il nodo iniziale è uguale sostituisci, altrimenti cerca il nodo iniziale di soluzion in path e sostituisci da li
            self.travel_time += time
            return path

        max_distance = self.battery_capacity * ambient_temperature/(self.electric_constant*speed)
        # Altrimenti, trova la stazione di ricarica più vicina e richiama la funzione
        charging_station_start = self.nearest_charging_station(graph, start, goal, solution, max_distance)
        if charging_station_start is not None:
            # Inizializza l'algoritmo di ricerca
            problem = PathFinding(graph, start, charging_station_start)
            # Inizializza l'algoritmo di ricerca A*
            astar = AStar(graph, h.euclidean_distance, view=True)
            solution = astar.solve(problem)
            if solution is None:
                return None
            path += solution

            for i, j in solution:
                self.travel_time += graph.edges[i, j].get('travel_time', 10)

            # Ricarica la batteria vediamo che metodo usare
            self.energy_recharged.append(self.battery_capacity - self.battery)
            self.travel_time += (self.battery_capacity - self.battery) / 22
            self.battery = self.battery_capacity # da fare
            
            self.recharge += 1
            graph.nodes[charging_station_start]['charging_station'] = False

            return self.adaptive_search(graph, charging_station_start, goal, ambient_temperature, path)

        # Se non ci sono stazioni di ricarica raggiungibili, restituisci None
        return None
    
    def smart_charge(self, graph, current_location, goal, ambient_temperature): #boh
        # Calcola la distanza alla prossima stazione di ricarica
        next_charging_station = self.nearest_charging_station(graph, current_location, goal)
        if next_charging_station is None:
            return False

        distance_to_next_station = h.euclidean_distance(current_location, next_charging_station, graph)
        speed = graph.edges[current_location, next_charging_station].get('speed_kph', 50)
        energy_needed_to_reach_next_station = self.electric_constant * (distance_to_next_station / 1000) * speed / ambient_temperature

        # Calcola l'energia necessaria per raggiungere la destinazione finale
        distance_to_goal = h.euclidean_distance(next_charging_station, goal, graph)
        energy_needed_to_reach_goal = self.electric_constant * (distance_to_goal / 1000) * speed / ambient_temperature

        # Calcola l'energia totale necessaria
        total_energy_needed = energy_needed_to_reach_next_station + energy_needed_to_reach_goal

        # Se l'energia totale necessaria è superiore alla capacità della batteria, ricarica al massimo
        if total_energy_needed > self.battery_capacity:
            self.battery = self.battery_capacity
        else:
            # Altrimenti, ricarica solo l'energia necessaria
            self.battery = total_energy_needed

        self.energy_recharged.append(self.battery_capacity - self.battery)
        self.recharge += 1
        return True

    # def adaptive_search(graph, start, goal, min_battery_percent, max_battery_capacity, battery, ambient_temperature, electric_constant, path=[]):
    #     while True:
    #         # Inizializza l'algoritmo di ricerca
    #         problem = PathFinding(graph, start, goal)
    #         # Inizializza l'algoritmo di ricerca A*
    #         astar = AStar(graph, h.euclidean_distance, view=True)
    #         solution = astar.solve(problem)
    #         if solution is None:
    #             return None

    #         # Calcola la distanza, la velocità e l'energia consumata
    #         distance = speed = energy_consumed = 0
    #         for i, j in solution:
    #             distance = graph.edges[i, j].get('length', 10)
    #             speed = graph.edges[i, j].get('speed_kph', 50)
    #             energy_consumed += electric_constant * (distance / 1000) * speed / ambient_temperature

    #         # Se l'energia consumata è inferiore alla capacità massima della batteria, restituisci il percorso
    #         if energy_consumed < battery - min_battery_percent:
    #             path += solution
    #             return path

    #         max_distance = max_battery_capacity*ambient_temperature/(electric_constant*speed)
    #         # Altrimenti, trova la stazione di ricarica più vicina
    #         charging_station_start = nearest_charging_station(graph, start, goal, solution, max_distance * 0.8)
    #         if charging_station_start is None:
    #             return None

    #         # Inizializza l'algoritmo di ricerca
    #         problem = PathFinding(graph, start, charging_station_start)
    #         # Inizializza l'algoritmo di ricerca A*
    #         astar = AStar(graph, h.euclidean_distance, view=True)
    #         solution = astar.solve(problem)
    #         if solution is None:
    #             return None
    #         path += solution
    #         battery = max_battery_capacity
    #         graph.nodes[charging_station_start]['charging_station'] = False

    #         # Aggiorna il punto di partenza per la prossima iterazione
    #         start = charging_station_start

    def nearest_charging_station(self, graph, start, goal, solution, raggio):
        # Ottieni tutte le stazioni di ricarica
        charging_stations = [node for node in graph.nodes() if graph.nodes[node].get('charging_station', False)]
        distanza_minima = float('inf')
        best_station = None
        distance = 0

        for i, j in solution: # Calcola 80% distanza percorso migliore
            distance += graph.edges[i, j].get('length', 10) / 1000
            if distance > raggio * 0.8:
                start = i
                raggio -= distance
                break

        for station in charging_stations: # Trova la stazione di ricarica più vicina al punto del percorso
            start_dist = h.euclidean_distance(start, station, graph)
            goal_dist = h.euclidean_distance(goal, station, graph)
            # Verifica se la stazione è all'interno della circonferenza
            if start_dist <= raggio:
                # Verifica se la stazione è la più vicina al perimetro e al goal
                if start_dist + goal_dist < distanza_minima:
                    distanza_minima = start_dist + goal_dist
                    best_station = station

        return best_station

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
    