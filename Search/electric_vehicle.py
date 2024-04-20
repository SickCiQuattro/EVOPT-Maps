from ASTAR import AStar, AstarNode
from queue import PriorityQueue

class ElectricVehicleNode(AstarNode): # A* search algorithm modificato per veicoli elettrici
    def __init__(self, state, parent=None, action=None, g=0, h=0, battery=20):
        super().__init__(state, parent, action, g, h)
        self.battery = battery

    def __lt__(self, other):
        return (self.g + self.h, self.battery) < (other.g + other.h, other.battery)

class ElectricVehicleAStar(AStar): 
    def __init__(self, graph, heuristic=lambda x, y, g: 0, view=False, battery_capacity=20):
        super().__init__(heuristic, view)
        self.graph = graph
        self.battery_capacity = battery_capacity

    def solve(self, problem):
        reached = set() # Insieme degli stati raggiunti
        frontier = PriorityQueue() # Coda di priorità
        frontier.put(ElectricVehicleNode(problem.init, h=self.heuristic(problem.init, problem.goal), battery=self.battery_capacity)) # Inserisce il nodo iniziale
        reached.add((problem.init, self.battery_capacity)) # Aggiunge il nodo iniziale all'insieme degli stati raggiunti
        self.reset_expanded() # Resetta il numero di nodi espansi

        while not frontier.empty(): # Finchè la coda di priorità non è vuota
            n = frontier.get() # Estrae il nodo con priorità più alta
            if problem.isGoal(n.state): # Se il nodo è lo stato obiettivo
                return self.extract_solution(n) # Estrae la soluzione
            for action, s, cost in problem.getSuccessors(n.state): # Per ogni azione, stato e costo dei successori dello stato corrente
                new_battery = n.battery - cost # Calcola la nuova batteria
                if new_battery > 0: # Se la batteria è maggiore di 0
                    if problem.is_charging_station(n.state): # Se lo stato corrente è una stazione di ricarica
                        new_battery = self.battery_capacity # La batteria viene ricaricata
                    new_state = (s, new_battery) # Calcola il nuovo stato
                    if new_state not in reached: # Se il nuovo stato non è stato raggiunto
                        self.update_expanded(s) # Aggiorna il numero di nodi espansi
                        reached.add(new_state) # Aggiunge il nuovo stato all'insieme degli stati raggiunti
                        new_g = n.g + cost # Calcola il nuovo costo
                        new_h = self.heuristic(s, problem.goal, self.graph) # Calcola la nuova euristica
                        frontier.put(ElectricVehicleNode(s, n, action, new_g, new_h, new_battery)) # Inserisce il nuovo nodo nella coda di priorità

        return None