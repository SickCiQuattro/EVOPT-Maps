from search_algorithm import SearchAlgorithm
from queue import PriorityQueue
from search_algorithm import Node

class AstarNode(Node):
    def __init__(self, state, parent = None, action = None, g = 0, h = 0) -> None:
        self.h = h
        super().__init__(state, parent, action, g)
        
    def __lt__(self, other):
        return self.g + self.h < other.g + other.h 
    
class UCS(SearchAlgorithm):
    """UCS Uniform Cost Search

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
        frontier.put(AstarNode(problem.init, h=0))
        reached.add(problem.init)
        self.reset_expanded()

        while frontier:
            n = frontier.get()
            if problem.isGoal(n.state):
                return self.extract_solution(n)
            for a, s in problem.getSuccessors(n.state):
                if s not in reached:
                    self.update_expanded(s)
                    reached.add(s)
                    new_g = n.g + 1
                    frontier.put(AstarNode(s, n, a, new_g, 0))

        return None