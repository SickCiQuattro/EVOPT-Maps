from search_algorithm import SearchAlgorithm
from queue import PriorityQueue
from search_algorithm import Node

class AstarNode(Node):
    def __init__(self, state, parent = None, action = None, g = 0, h = 0) -> None:
        self.h = h
        super().__init__(state, parent, action, g)
        
    def __lt__(self, other):
        return self.g + self.w * self.h < other.g + other.w * other.h 
    
class AStar(SearchAlgorithm):
    """AStar First Search

    Args:
        Solver (_type_): This is an implementation for the Solver class
    """
    def __init__(self, heuristic = lambda x,y : 0, view = False, w = 1) -> None:
        self.heuristic = heuristic
        self.w = w
        super().__init__(view)

    def solve(self, problem):
        reached = set()
        frontier = PriorityQueue()
        frontier.put(AstarNode(problem.init, h=self.heuristic(problem.init, problem.goal)))
        reached.add(problem.init)
        self.reset_expanded()

        while frontier: #while not frontier.empty():
            n = frontier.get()
            if problem.isGoal(n.state):
                return self.extract_solution(n)
            for a, s, cost in problem.getSuccessors(n.state):  # <-- Accessing cost here
                if s not in reached:  # and cost is acceptable (if needed)
                    self.update_expanded(s)
                    reached.add(s)
                    new_g = n.g + cost  # <-- Using cost for g calculation
                    new_h = self.heuristic(s, problem.goal)
                    frontier.put(AstarNode(s, n, a, new_g, new_h))

        return None