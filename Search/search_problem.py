class SearchProblem:
    """Rappresenta un problema di ricerca generico.

    Args:
        init: Il nodo iniziale.
        goal: Il nodo obiettivo.
        graph: Il grafo su cui eseguire la ricerca.
        charging_stations: (Opzionale) Una lista di stazioni di ricarica.
        min_battery_at_goal: (Opzionale) La quantità minima di batteria richiesta al raggiungimento dell'obiettivo.
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
        electric_constant = 0.06
        successors = set()
        for neighbor in self.graph.neighbors(state):
            action = (state, neighbor)
            distance = self.graph.edges[state, neighbor].get('length', 100) # Distanza in metri
            speed = self.graph.edges[state, neighbor].get('speed_kph', 50)  # Velocità in km/h
            energy_consumed = electric_constant * (distance / 1000) * speed # k * d(km) * v(km/h) = kWh * °C

            time = self.graph.edges[state, neighbor].get('travel_time', 10) # Tempo di percorrenza in secondi
            successors.add((action, neighbor, energy_consumed, time))
        return successors

    def isGoal(self, state, battery_level):
        """Verifica se uno stato è l'obiettivo, considerando anche il livello della batteria.

        Args:
            state: Lo stato da verificare.
            battery_level: Il livello attuale della batteria.

        Returns:
            True se lo stato è l'obiettivo e il livello della batteria è sufficiente, altrimenti False.
        """
        return state == self.goal and battery_level >= self.veicle.min_battery
    
    def isGoal(self, state):
        """Verifica se uno stato è l'obiettivo, senza considerare il livello della batteria.

        Args:
            state: Lo stato da verificare.

        Returns:
            True se lo stato è l'obiettivo, altrimenti False.
        """
        return state == self.goal

    def is_charging_station(self, state):
        """Verifica se uno stato è una stazione di ricarica.

        Args:
            state: Lo stato da verificare.

        Returns:
            True se lo stato è una stazione di ricarica, altrimenti False.
        """
        return state in self.charging_stations
