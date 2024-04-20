class Node:
    def __init__(self, state, parent=None, action=None, g=0): # Nodo di ricerca
        self.state = state # Stato corrente
        self.parent = parent # Nodo padre
        self.action = action # Azione che ha portato allo stato corrente
        self.g = g # Costo del percorso

class SearchAlgorithm: # Algoritmo di ricerca
    def __init__(self, view=False): # Inizializza l'algoritmo di ricerca
        self.expanded = 0 # Numero di nodi espansi
        self.expanded_states = set() # Insieme degli stati espansi
        self.view = view # Visualizzazione

    def solve(self, problem): # Risolve il problema di ricerca
        raise NotImplementedError("This method should be implemented by subclasses.")

    def update_expanded(self, state): # Aggiorna il numero di nodi espansi
        if self.view:
            self.expanded_states.add(state)
        self.expanded += 1

    def reset_expanded(self): # Resetta il numero di nodi espansi
        if self.view:
            self.expanded_states = set()
        self.expanded = 0

    def extract_solution(self, node): # Estrae la soluzione
        solution = []
        while node.parent is not None:
            solution.insert(0, node.action)
            node = node.parent
        return solution
