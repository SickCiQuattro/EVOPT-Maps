from electric_vehicle import ElectricVehicle as ev
from queue import PriorityQueue
from ASTAR import AStar, AstarNode

class ElectricVehicleNode(AstarNode): # Nodo per la ricerca A* con veicolo elettrico 
    def __init__(self, state, parent = None, action = None, g = 0, h = 0, battery = 0):
        super().__init__(state, parent, action, g, h)
        self.battery = battery

    def __lt__(self, other): # Confronta due nodi
        return self.g + self.h < other.g + other.h

class ElectricVehicleAStar(AStar):
    def __init__(self, graph, heuristic, view = False, temperature = 20, vehicle = None, charging_stations = None):
        super().__init__(graph, heuristic, view)
        self.temperature = temperature
        self.vehicle = vehicle
        self.charging_stations = charging_stations

    def solve(self, problem):
        reached = set()
        frontier = PriorityQueue()
        frontier.put(ElectricVehicleNode(problem.init, h=self.heuristic(problem.init, problem.goal, self.graph), battery=self.vehicle.battery))
        reached.add((problem.init, self.vehicle.battery))
        self.reset_expanded()

        while not frontier.empty():
            n = frontier.get()
            if problem.isGoalBattery(n.state, n.battery, self.vehicle.min_battery):
                return self.extract_solution(n)
            for action, s, cost, time in problem.getSuccessors(n.state):
                new_battery = n.battery - (cost * self.vehicle.electric_constant / self.temperature)
                if new_battery > 0:
                    charging_time = 0
                    if problem.is_charging_station(n.state, self.charging_stations):
                        recharge_needed = self.vehicle.calculate_recharge_needed(n.state, problem.goal, self.graph, self.temperature)
                        self.vehicle.energy_recharged.append(recharge_needed)
                        self.vehicle.travel_time += (recharge_needed) / 22 * 3600
                        new_battery += recharge_needed
                        self.vehicle.recharge += 1
                    new_g = n.g + (time / 3600) + charging_time
                    new_state = (s, new_battery)
                    if new_state not in reached:
                        self.update_expanded(s)
                        reached.add(new_state)
                        new_h = self.heuristic(s, problem.goal, self.graph)
                        frontier.put(ElectricVehicleNode(s, n, action, new_g, new_h, battery=new_battery))
        return None
