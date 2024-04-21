from ASTAR import AStar, AstarNode
from queue import PriorityQueue

TEMPERATURE_EFFECT = 0.1

def temperature_effect(temperature): # Effetto della temperatura sulla batteria
    return max(1 - ((20 - temperature) * TEMPERATURE_EFFECT), 0)

class ElectricVehicleNode(AstarNode): # Nodo per l'algoritmo A* con veicolo elettrico
    def __init__(self, state, parent=None, action=None, g=0, h=0, battery=100, temperature=20):
        super().__init__(state, parent, action, g, h)
        self.battery = battery
        self.temperature = temperature

    def __lt__(self, other): # Confronta due nodi
        return (self.g + self.h, self.battery) < (other.g + other.h, other.battery)

class ElectricVehicleAStar(AStar): # A* search algorithm con veicolo elettrico
    def __init__(self, graph, heuristic, view=False, battery_capacity=100, min_battery=20, temperature=20):
        super().__init__(heuristic, view)
        self.graph = graph
        self.battery_capacity = battery_capacity
        self.min_battery = min_battery
        self.temperature = temperature

    def solve(self, problem): # Risolve il problema
        reached = set() # Insieme degli stati raggiunti
        frontier = PriorityQueue() # Coda di priorità
        frontier.put(ElectricVehicleNode(problem.init, h=self.heuristic(problem.init, problem.goal), battery=self.battery_capacity)) # Inserisce il nodo iniziale
        reached.add((problem.init, self.battery_capacity)) # Aggiunge il nodo iniziale all'insieme degli stati raggiunti
        self.reset_expanded() # Resetta il numero di nodi espansi

        while not frontier.empty(): # Finchè la coda di priorità non è vuota
            n = frontier.get() # Estrae il nodo con priorità più alta
            if problem.isGoal(n.state, self.battery_capacity): # Se il nodo è lo stato obiettivo
                return self.extract_solution(n) # Estrae la soluzione
            for action, s, cost in problem.getSuccessors(n.state): # Per ogni azione, stato e costo dei successori dello stato corrente
                new_battery = (n.battery - cost) * temperature_effect(self.temperature) # Calcola la nuova batteria
                if new_battery > 0: # Se la batteria è maggiore di 0
                    if problem.is_charging_station(n.state): # Se il nodo corrente è una stazione di ricarica
                        new_battery = self.battery_capacity # La batteria viene ricaricata
                    new_state = (s, new_battery) # Calcola il nuovo stato
                    if new_state not in reached: # Se il nuovo stato non è stato raggiunto
                        self.update_expanded(s) # Aggiorna il numero di nodi espansi
                        reached.add(new_state) # Aggiunge il nuovo stato all'insieme degli stati raggiunti
                        new_g = n.g + cost # Calcola il nuovo costo
                        new_h = self.heuristic(s, problem.goal, self.graph) # Calcola la nuova euristica
                        frontier.put(ElectricVehicleNode(s, n, action, new_g, new_h, new_battery)) # Inserisce il nuovo nodo nella coda di priorità

        return None
