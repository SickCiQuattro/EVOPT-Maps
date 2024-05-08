from search_problem import SearchProblem
"""
Modulo path_finding.py

Questo modulo contiene la classe PathFinding, che estende la classe SearchProblem per risolvere specifici problemi di ricerca del percorso su un grafo. 
La classe PathFinding definisce il problema di ricerca del percorso specificando il grafo, il nodo iniziale e il nodo obiettivo.
"""

class PathFinding(SearchProblem):
    """
    Classe per risolvere un problema di ricerca del percorso su un grafo.

    Questa classe estende la classe SearchProblem e aggiunge la logica specifica per la ricerca del percorso su un grafo. Il grafo, il nodo iniziale e il nodo obiettivo sono specificati al momento della creazione dell'istanza della classe.

    Args:
        graph (Graph): Il grafo su cui eseguire la ricerca del percorso.
        init (int): L'ID del nodo iniziale del percorso.
        goal (int): L'ID del nodo obiettivo del percorso.
    """
    def __init__(self, graph, init, goal):
        """
        Inizializza una nuova istanza della classe PathFinding.

        Args:
            graph (Graph): Il grafo su cui eseguire la ricerca del percorso.
            init (int): L'ID del nodo iniziale del percorso.
            goal (int): L'ID del nodo obiettivo del percorso.
        """
        super().__init__(init, goal, graph)
