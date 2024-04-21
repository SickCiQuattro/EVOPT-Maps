class SearchProblem:
    def __init__(self, init, goal, graph, charging_stations, min_battery_at_goal):
        self.init = init
        self.goal = goal
        self.graph = graph
        self.charging_stations = charging_stations
        self.min_battery_at_goal = min_battery_at_goal

    def getSuccessors(self, state):
        successors = set()
        for neighbor in self.graph.neighbors(state):
            action = (state, neighbor)
            distance = self.graph.edges[state, neighbor].get('length', 1)  # Use 'length' for distance
            successors.add((action, neighbor, distance))
        return successors

    def isGoal(self, state, battery_level):
        return state == self.goal and battery_level >= self.min_battery_at_goal

    def is_charging_station(self, state):
        return state in self.charging_stations