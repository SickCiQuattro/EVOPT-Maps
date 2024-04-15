from search_algorithm import SearchAlgorithm, Node
from queue import PriorityQueue
from ASTAR import AStar

class ElectricVehicleNode(Node):
    def __init__(self, state, parent=None, action=None, g=0, h=0, battery=20) -> None:
        super().__init__(state, parent, action, g)
        self.h = h
        self.battery = battery  # Aggiungi qui lo stato della batteria

    def __lt__(self, other):
        return (self.g + self.h, self.battery) < (other.g + other.h, other.battery)

    def is_charging_station(self, charging_stations):
        return self.state in charging_stations

class ElectricVehicleAStar(AStar):
    def __init__(self, heuristic=lambda x, y: 0, view=False, w=1, battery_capacity=20) -> None:
        super().__init__(heuristic, view, w)
        self.battery_capacity = battery_capacity
        

    def solve(self, problem):
        reached = set()
        frontier = PriorityQueue()
        frontier.put(ElectricVehicleNode(problem.init, h=self.heuristic(problem.init, problem.goal), battery=self.battery_capacity))
        reached.add((problem.init, self.battery_capacity))
        self.reset_expanded()

        while not frontier.empty():
            n = frontier.get()
            if problem.isGoal(n.state):
                return self.extract_solution(n)
            for a, s, cost in problem.getSuccessors(n.state):
                new_battery = n.battery - cost  # Assume cost is also the battery consumption
                if new_battery > 0:  # Ensure the battery doesn't run out
                    # Controlla se il nodo corrente è una stazione di ricarica
                    if problem.is_charging_station(n.state):  # Modifica qui
                        new_battery = self.battery_capacity  # Recharge the battery
                    new_state = (s, new_battery)
                    if new_state not in reached:
                        self.update_expanded(s)
                        reached.add(new_state)
                        new_g = n.g + cost
                        new_h = self.heuristic(s, problem.goal)
                        frontier.put(ElectricVehicleNode(s, n, a, new_g, new_h, new_battery))

        return None
