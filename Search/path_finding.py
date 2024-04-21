from search_problem import SearchProblem

class PathFinding(SearchProblem):
    def __init__(self, graph, init, goal, charging_stations, min_battery_at_goal):
        super().__init__(init, goal, graph, charging_stations, min_battery_at_goal)

#tutta sta roba non penso ci servirà ancora ma la lascio qua per sicurezza
# class PathFinding(SearchProblem):
#     def __init__(self, world, init, goal, charging_stations):
#         actions = ['N', 'S', 'W', 'E']
#         cost = 1  # Assume uniform cost for simplicity
#         super().__init__(init, goal, actions, world, cost, charging_stations)  # Passa charging_stations qui
#         self.charging_stations = charging_stations  # Add charging stations

#     def getSuccessors(self, state) -> set:
#         succ = set()
#         for a in self.actions:
#             next_state = self.result(state, a)
#             if self.is_valid(next_state):
#                 succ.add((a, next_state, self.cost))  # Add cost as the third element of the tuple
#         return succ

#     def result(self, state, action):
#         # Define how actions change the state
#         x, y = state
#         if action == 'N':
#             return (x, y + 1)
#         elif action == 'S':
#             return (x, y - 1)
#         elif action == 'E':
#             return (x + 1, y)
#         elif action == 'W':
#             return (x - 1, y)

#     def is_valid(self, state):
#         # Check if the state is valid (not a wall and within map limits)
#         x, y = state
#         return (0 <= x <= self.world.x_lim and
#                 0 <= y <= self.world.y_lim and
#                 state not in self.world.walls)

#     def isGoal(self, state):
#         return state == self.goal

#     def is_charging_station(self, state) -> bool:
#         # Check if the current state is a charging station
#         return state in self.charging_stations

#     class World:
#         def __init__(self, x_lim, y_lim, walls):
#             self.x_lim = x_lim
#             self.y_lim = y_lim
#             self.walls = walls

#         def __str__(self):
#             ret = ""
#             for x in range(self.x_lim + 1):
#                 for y in range(self.y_lim + 1):
#                     if (x, y) in self.walls:
#                         ret += "%"
#                     else:
#                         ret += " "
#                 ret += "\n"
#             return ret