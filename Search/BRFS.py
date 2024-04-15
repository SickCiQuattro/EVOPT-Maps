from search_algorithm import SearchAlgorithm
from queue import Queue
from search_algorithm import Node

class BrFS(SearchAlgorithm):
    """Breath First Search

    Args:
        Solver (_type_): This is an implementation for the Solver class
    """
    def solve(self, problem) -> list:
        reached = set()
        frontier = Queue()
        frontier.put(Node(problem.init))
        reached.add(problem.init)
        self.reset_expanded()
        while (not frontier.empty()):
            n = frontier.get()
            if (problem.isGoal(n.state)):
                return self.extract_solution(n)
            for a,s in problem.getSuccessors(n.state):
                if s not in reached:
                    self.update_expanded(s)
                    reached.add(s)
                    frontier.put(Node(s,n,a,n.g+1))
        return None