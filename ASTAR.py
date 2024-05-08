from search_algorithm import SearchAlgorithm, Node
from queue import PriorityQueue
"""
Implementazione dell'algoritmo di ricerca A*.

Questo modulo fornisce una implementazione dell'algoritmo di ricerca A*.
Include una classe `AstarNode` per rappresentare i nodi nell'algoritmo A* e una classe `AStar` per l'algoritmo stesso.

Esempio di utilizzo:

```python
from ASTAR import AStar, AstarNode

# Definisci il tuo grafo, la tua euristica e il tuo problema
graph = ...
heuristic = ...
problem = ...

# Crea un'istanza dell'algoritmo A*
astar = AStar(graph, heuristic)

# Risolvi il problema
solution = astar.solve(problem)
"""

class AstarNode(Node):
    """
    Nodo per l'algoritmo A*.

    Args:
        state (object): Lo stato del nodo.
        parent (AstarNode, optional): Il nodo genitore. Default è None.
        action (object, optional): L'azione che ha portato a questo nodo. Default è None.
        g (int or float, optional): Il costo per raggiungere questo nodo. Default è 0.
        h (int or float, optional): L'euristica per questo nodo. Default è 0.
    """
    def __init__(self, state, parent = None, action = None, g = 0, h = 0): # Costruttore
        super().__init__(state, parent, action, g)
        self.h = h

    def __lt__(self, other): # Confronta due nodi
        return self.g + self.h < other.g + other.h

class AStar(SearchAlgorithm):
    """
    Implementazione dell'algoritmo di ricerca A*.

    Args:
        graph (object): Il grafo su cui eseguire l'algoritmo.
        heuristic (function): La funzione euristica da utilizzare.
        view (bool, optional): Se True, visualizza l'output dell'algoritmo. Default è False.
    """
    def __init__(self, graph, heuristic, view = False):
        self.graph = graph
        self.heuristic = heuristic
        super().__init__(view)

    def solve(self, problem):
        """
        Risolve il problema utilizzando l'algoritmo A*.

        Args:
            problem (object): Il problema da risolvere.

        Returns:
            object: La soluzione al problema, se esiste. Altrimenti, None.
        """
        reached = set() # Insieme degli stati raggiunti
        frontier = PriorityQueue() # Coda di priorità
        frontier.put(AstarNode(problem.init, h = self.heuristic(problem.init, problem.goal, self.graph))) # Inserisce il nodo iniziale
        reached.add(problem.init) # Aggiunge il nodo iniziale all'insieme degli stati raggiunti
        self.reset_expanded() # Resetta il numero di nodi espansi

        while not frontier.empty(): # Finchè la coda di priorità non è vuota
            n = frontier.get() # Estrae il nodo con priorità più alta
            if problem.isGoal(n.state): # Se il nodo è lo stato obiettivo
                return self.extract_solution(n) # Estrae la soluzione
            for action, s, cost, t in problem.getSuccessors(n.state): # Per ogni azione, stato e costo dei successori dello stato corrente
                if s not in reached: # Se il nuovo stato non è stato raggiunto
                    self.update_expanded(s) # Aggiorna il numero di nodi espansi
                    reached.add(s) # Aggiunge il nuovo stato all'insieme degli stati raggiunti
                    new_g = n.g + cost # Calcola il nuovo costo
                    new_h = self.heuristic(s, problem.goal, self.graph) # Calcola la nuova euristica
                    frontier.put(AstarNode(s, n, action, new_g, new_h)) # Inserisce il nuovo nodo nella coda di priorità

        return None