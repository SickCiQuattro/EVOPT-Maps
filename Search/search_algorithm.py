class Node:
    """Rappresenta un nodo in un algoritmo di ricerca.

    Args:
        state: Lo stato corrente del nodo.
        parent: Il nodo genitore.
        action: L'azione che ha portato a questo stato.
        g: Il costo del percorso per arrivare a questo nodo.
    """
    def __init__(self, state, parent=None, action=None, g=0): # Nodo di ricerca
        self.state = state # Stato corrente
        self.parent = parent # Nodo padre
        self.action = action # Azione che ha portato allo stato corrente
        self.g = g # Costo del percorso

class SearchAlgorithm:
    """Classe base per un algoritmo di ricerca.

    Args:
        view: Se True, visualizza l'output dell'algoritmo.
    """
    def __init__(self, view=False): # Inizializza l'algoritmo di ricerca
        self.expanded = 0 # Numero di nodi espansi
        self.expanded_states = set() # Insieme degli stati espansi
        self.view = view # Visualizzazione

    def solve(self, problem):
        """Risolve il problema di ricerca.

        Questo metodo dovrebbe essere implementato dalle sottoclassi.

        Args:
            problem: Il problema da risolvere.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def update_expanded(self, state):
        """Aggiorna il numero di nodi espansi.

        Args:
            state: Lo stato del nodo da aggiungere all'insieme degli stati espansi.
        """
        if self.view:
            self.expanded_states.add(state)
        self.expanded += 1

    def reset_expanded(self):
        """Resetta il numero di nodi espansi."""
        if self.view:
            self.expanded_states = set()
        self.expanded = 0

    def extract_solution(self, node):
        """Estrae la soluzione a partire da un nodo.

        Args:
            node: Il nodo da cui estrarre la soluzione.

        Returns:
            Una lista delle azioni che portano alla soluzione.
        """
        solution = []
        while node.parent is not None:
            solution.insert(0, node.action)
            node = node.parent
        return solution
