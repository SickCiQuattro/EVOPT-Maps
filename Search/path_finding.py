from search_problem import SearchProblem

class PathFinding(SearchProblem):
    """Problema di ricerca per il percorso.

    Eredita da SearchProblem e aggiunge la logica specifica per la ricerca del percorso.

    Args:
        graph: Il grafo su cui eseguire la ricerca.
        init: Il nodo iniziale.
        goal: Il nodo obiettivo.
        charging_stations: (Opzionale) Una lista di stazioni di ricarica.
        min_battery_at_goal: (Opzionale) La quantità minima di batteria richiesta al raggiungimento dell'obiettivo.
    """

    def __init__(self, graph, init, goal):
        super().__init__(init, goal, graph)
