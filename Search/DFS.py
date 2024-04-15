from search_algorithm import SearchAlgorithm
from queue import LifoQueue
from search_algorithm import Node

class DFS(SearchAlgorithm):
    """Depth First Search"""

    def solve(self, problem) -> list:
        reached = set()
        frontier = LifoQueue()
        frontier.put(Node(problem.init))
        reached.add(problem.init)
        self.reset_expanded()

        while frontier:
            n = frontier.get_nowait()
            if problem.isGoal(n.state):
                return self.extract_solution(n)
            for a, s in problem.getSuccessors(n.state):
                if s not in reached:
                    self.update_expanded(s)
                    reached.add(s)
                    frontier.put(Node(s, n, a, n.g + 1))

        return None
