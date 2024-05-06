class SearchProblem:
    """Classe per risolvere un problema di ricerca.

    Questa classe definisce un problema di ricerca generico.

    Args:
        init (int): Il nodo iniziale.
        goal (int): Il nodo obiettivo.
        graph (networkx.classes.multidigraph.MultiDiGraph): Il grafo su cui eseguire la ricerca.
    """

    def __init__(self, init, goal, graph):
        self.init = init
        self.goal = goal
        self.graph = graph

    def getSuccessors(self, state):
        """Restituisce i successori di uno stato.

        Args:
            state: Lo stato di cui ottenere i successori.

        Returns:
            Un insieme di tuple, ognuna delle quali contiene un'azione, un successore, l'energia consumata per raggiungere il successore e il tempo impiegato.
        """
        successors = set()
        for neighbor in self.graph.neighbors(state):
            edge_data = self.graph.edges[state, neighbor]
            action = (state, neighbor)
            distance = edge_data.get('length', 100) # Distanza in metri
            speed = edge_data.get('speed_kph', 50)  # Velocità in km/h
            energy_consumed = (distance / 1000) * speed # d(km) * v(km/h) manca costante elettrica / temperatura
            time = edge_data.get('travel_time', 10) # Tempo di percorrenza in secondi
            successors.add((action, neighbor, energy_consumed, time))
        return successors
    
    def isGoal(self, state):
        """Verifica se uno stato è l'obiettivo, senza considerare il livello della batteria.

        Args:
            state: Lo stato da verificare.

        Returns:
            True se lo stato è l'obiettivo, altrimenti False.
        """
        return state == self.goal

    def is_charging_station(self, state, charging_stations):
        """Verifica se uno stato è una stazione di ricarica.

        Args:
            state (int): Il nodo da verificare.
            charging_stations (list): La lista delle stazioni di ricarica.

        Returns:
            bool: True se lo stato è una stazione di ricarica, altrimenti False.
        """
        return state in charging_stations
