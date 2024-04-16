class SearchProblem(object):

    def __init__(self, init, goal, actions, world, cost, charging_stations):
        self.init = init
        self.goal = goal
        self.actions = actions
        self.world = world
        self.cost = cost
        self.charging_stations = charging_stations
        
    def getSuccessors(self, state) -> set:
        successors = set()
        for action in self.actions:
            # Calcola la nuova posizione in base all'azione
            new_state = self.result(state, action)
            if self.is_valid(new_state):
                cost = self.cost.get(action, 1)  # Ottieni il costo dell'azione
                successors.add((action, new_state, cost))
        return successors

    def isGoal(self, state) -> bool:
        return state == self.goal

    def result(self, state, action):
        # Definisci come le azioni cambiano lo stato
        x, y = state
        if action == 'N':
            return (x, y+1)
        elif action == 'S':
            return (x, y-1)
        elif action == 'E':
            return (x+1, y)
        elif action == 'W':
            return (x-1, y)

    def is_valid(self, state):
        # Verifica se lo stato è valido (non è una parete e si trova all'interno dei limiti della mappa)
        x, y = state
        return (0 <= x < self.world.width and
                0 <= y < self.world.height and
                state not in self.world.walls)

    def is_charging_station(self, state) -> bool:
        # Verifica se lo stato corrente è una stazione di ricarica
        return state in self.charging_stations