from ASTAR import AStar, AstarNode
from queue import PriorityQueue

# Costanti per la simulazione
TEMPERATURE_EFFECT = 0.1
CHARGING_RATE = 0.5  # Percentuale di batteria caricata per minuto

def temperature_effect(temperature):
    """Calcola l'effetto della temperatura sulla batteria."""
    return max(1 - ((20 - temperature) * TEMPERATURE_EFFECT), 0)

class ElectricVehicleNode(AstarNode):
    def __init__(self, state, parent=None, action=None, g=0, h=0, battery=100, temperature=20, time=0):
        super().__init__(state, parent, action, g, h)
        self.battery = battery
        self.temperature = temperature
        self.time = time  # Aggiunto il tempo al nodo

    def __lt__(self, other):
        return (self.g + self.h, self.battery) < (other.g + other.h, other.battery)

class ElectricVehicleAStar(AStar):
    def __init__(self, graph, heuristic, view=False, battery_capacity=100, min_battery=20, temperature=20):
        super().__init__(heuristic, view)
        self.graph = graph
        self.battery_capacity = battery_capacity
        self.min_battery = min_battery
        self.temperature = temperature

    def solve(self, problem):
        reached = set()
        frontier = PriorityQueue()
        frontier.put(ElectricVehicleNode(problem.init, h=self.heuristic(problem.init, problem.goal), battery=self.battery_capacity))
        reached.add((problem.init, self.battery_capacity, 0))  # Aggiunto il tempo iniziale

        while not frontier.empty():
            n = frontier.get()
            if problem.isGoal(n.state, n.battery):
                return self.extract_solution(n)
            for action, s, cost in problem.getSuccessors(n.state):
                travel_time = self.graph.edges[action]['travel_time']  # Tempo di viaggio tra i nodi
                new_battery = n.battery - cost * temperature_effect(self.temperature)
                new_time = n.time + travel_time  # Aggiorna il tempo totale di viaggio

                if new_battery > 0:
                    if problem.is_charging_station(n.state):
                        # Calcola il tempo di ricarica necessario per raggiungere la capacità massima
                        charging_time = (self.battery_capacity - new_battery) / CHARGING_RATE
                        new_time += charging_time  # Aggiorna il tempo totale con il tempo di ricarica
                        new_battery = self.battery_capacity  # Ricarica la batteria

                    new_state = (s, new_battery, new_time)
                    if new_state not in reached:
                        self.update_expanded(s)
                        reached.add(new_state)
                        new_g = n.g + cost
                        new_h = self.heuristic(s, problem.goal, self.graph)
                        frontier.put(ElectricVehicleNode(s, n, action, new_g, new_h, new_battery, self.temperature, new_time))
                        print(f"Passing through node: {s}")
                        print(f"Remaining battery: {new_battery}")
                        print(f"Total travel time: {new_time}")
                        if problem.is_charging_station(s):
                            print(f"Charging at station: {s}")
                            print(f"Charged battery to: {new_battery}")

        return None
