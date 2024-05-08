class Node:
    """
    Rappresenta un nodo in un algoritmo di ricerca.

    Ogni nodo ha uno stato, un nodo genitore, un'azione che ha portato a questo stato e un costo del percorso per arrivare a questo nodo.

    Args:
        state (any): Lo stato corrente del nodo.
        parent (Node, optional): Il nodo genitore. Default a None.
        action (any, optional): L'azione che ha portato a questo stato. Default a None.
        g (int or float, optional): Il costo del percorso per arrivare a questo nodo. Default a 0.
    """
    def __init__(self, state, parent = None, action = None, g = 0):
        self.state = state
        self.parent = parent
        self.action = action
        self.g = g

class SearchAlgorithm:
    """
    Classe base per un algoritmo di ricerca.

    Questa classe definisce l'interfaccia comune per tutti gli algoritmi di ricerca. Gli algoritmi specifici dovrebbero estendere questa classe e implementare il metodo `solve`.

    Args:
        view (bool, optional): Se True, visualizza l'output dell'algoritmo. Default a False.
    """
    def __init__(self, view = False): # Inizializza l'algoritmo di ricerca
        self.expanded = 0 # Numero di nodi espansi
        self.expanded_states = set() # Insieme degli stati espansi
        self.view = view # Visualizzazione

    def solve(self, problem):
        """
        Risolve il problema di ricerca.

        Questo metodo dovrebbe essere implementato dalle sottoclassi.

        Args:
            problem (SearchProblem): Il problema da risolvere.

        Raises:
            NotImplementedError: Se il metodo non è stato implementato dalla sottoclasse.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def update_expanded(self, state):
        """
        Aggiorna il numero di nodi espansi.

        Aggiunge lo stato del nodo all'insieme degli stati espansi e incrementa il conteggio dei nodi espansi.

        Args:
            state (any): Lo stato del nodo da aggiungere all'insieme degli stati espansi.
        """
        if self.view:
            self.expanded_states.add(state)
        self.expanded += 1

    def reset_expanded(self):
        """
        Resetta il numero di nodi espansi.

        Svuota l'insieme degli stati espansi e azzera il conteggio dei nodi espansi.
        """
        if self.view:
            self.expanded_states = set()
        self.expanded = 0

    def extract_solution(self, node):
        """
        Estrae la soluzione a partire da un nodo.

        Questo metodo dovrebbe essere implementato dalle sottoclassi.

        Args:
            node (Node): Il nodo finale da cui estrarre la soluzione.

        Raises:
            NotImplementedError: Se il metodo non è stato implementato dalla sottoclasse.
        """
        solution = []
        while node.parent is not None:
            solution.insert(0, node.action)
            node = node.parent
        return solution
