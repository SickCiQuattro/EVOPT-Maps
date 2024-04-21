from search_algorithm import SearchAlgorithm, Node
from queue import PriorityQueue
"""A* search algorithm implementation."""

class AstarNode(Node): # Nodo per l'algoritmo A*
    def __init__(self, state, parent=None, action=None, g=0, h=0): # Costruttore
        super().__init__(state, parent, action, g)
        self.h = h

    def __lt__(self, other): # Confronta due nodi
        return self.g + self.h < other.g + other.h

class AStar(SearchAlgorithm): # A* search algorithm
    def __init__(self, heuristic=lambda x, y: 0, view=False):
        self.heuristic = heuristic
        super().__init__(view)

    def solve(self, problem): # Risolve il problema
        reached = set() # Insieme degli stati raggiunti
        frontier = PriorityQueue() # Coda di priorità
        frontier.put(AstarNode(problem.init, h=self.heuristic(problem.init, problem.goal))) # Inserisce il nodo iniziale
        reached.add(problem.init) # Aggiunge il nodo iniziale all'insieme degli stati raggiunti
        self.reset_expanded() # Resetta il numero di nodi espansi

        while not frontier.empty(): # Finchè la coda di priorità non è vuota
            n = frontier.get() # Estrae il nodo con priorità più alta
            if problem.isGoal(n.state): # Se il nodo è lo stato obiettivo
                return self.extract_solution(n) # Estrae la soluzione
            for action, s, cost in problem.getSuccessors(n.state): # Per ogni azione, stato e costo dei successori dello stato corrente
                if s not in reached: # Se il nuovo stato non è stato raggiunto
                    self.update_expanded(s) # Aggiorna il numero di nodi espansi
                    reached.add(s) # Aggiunge il nuovo stato all'insieme degli stati raggiunti
                    new_g = n.g + cost # Calcola il nuovo costo
                    new_h = self.heuristic(s, problem.goal) # Calcola la nuova euristica
                    frontier.put(AstarNode(s, n, action, new_g, new_h)) # Inserisce il nuovo nodo nella coda di priorità

        return None