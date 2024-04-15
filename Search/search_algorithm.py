class Node:
    def __init__(self, state, parent = None, action = None, g = 0) -> None:
        self.state = state
        self.parent = parent
        self.action = action
        self.g = g
        
class SearchAlgorithm:
    def __init__(self, view = False) -> None:
        self.expanded = 0
        self.expanded_states = set()
        self.view = view
    def solve(self, problem) -> list:
        raise Exception("Not implemented")
    
    def update_expanded(self,state):
        if (self.view):
            self.expanded_states.add(state)
        self.expanded += 1
    def reset_expanded(self):
        if (self.view):
            self.expanded_states = set()
        self.expanded = 0
    def extract_solution(self,node) -> list:
        sol = list()
        while (node.parent is not None):
            sol.insert(0,node.action)
            node = node.parent
        return sol