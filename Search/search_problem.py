class SearchProblem(object): # Classe astratta
    def __init__(self, init, goal, graph, charging_stations):
        self.init = init # Stato iniziale
        self.goal = goal # Stato obiettivo
        self.graph = graph # Grafo
        self.charging_stations = charging_stations # Stazioni di ricarica

    def getSuccessors(self, state): # Ritorna i successori di uno stato
        successors = set() # Insieme dei successori
        for neighbor in self.graph.neighbors(state): # Per ogni vicino dello stato corrente
            action = (state, neighbor) # Azione
            cost = self.graph.edges[state, neighbor].get('weight', 1) # Costo
            successors.add((action, neighbor, cost)) # Aggiunge il successore all'insieme dei successori
        return successors

    # da implementare condizione di batteria minima per arrivare a destinazione
    def isGoal(self, state): # Verifica se uno stato è l'obiettivo
        return state == self.goal # Ritorna True se lo stato è l'obiettivo

    def is_charging_station(self, state): # Verifica se uno stato è una stazione di ricarica
        return state in self.charging_stations # Ritorna True se lo stato è una stazione di ricarica
