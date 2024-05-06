from search_problem import SearchProblem

class PathFinding(SearchProblem):
    """Classe per risolvere un problema di ricerca del percorso.

    Questa classe eredita da SearchProblem e aggiunge la logica specifica per la ricerca del percorso.

    Args:
        graph (Graph): Il grafo su cui eseguire la ricerca.
        init (int): Il nodo iniziale.
        goal (int): Il nodo obiettivo.
    """
    def __init__(self, graph, init, goal):
        super().__init__(init, goal, graph)
