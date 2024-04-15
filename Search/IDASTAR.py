from search_algorithm import SearchAlgorithm
from queue import LifoQueue  # Using LifoQueue for depth-first exploration

from search_algorithm import Node


class IDAStarNode(Node):
    def __init__(self, state, parent=None, action=None, g=0, h=0, threshold=float('inf')):
        self.h = h
        self.threshold = threshold
        super().__init__(state, parent, action, g)

    def __lt__(self, other):
        f_score = self.g + self.h
        other_f_score = other.g + other.h
        return f_score < other_f_score or (f_score == other_f_score and self.g < other.g)


class IDAStar(SearchAlgorithm):
    """Iterative Deepening A* Search

    Args:
        heuristic (_type_): This is a function that estimates the cost from a state to the goal.
        view (bool, optional): Whether to display the search progress (default: False).
        w (int, optional): Weight for the heuristic function (default: 1).
    """

    def __init__(self, heuristic=lambda x, y: 0, view=False, w=1):
        self.heuristic = heuristic
        self.w = w
        self.cutoff = float('inf')  # Initial threshold for iterative deepening
        super().__init__(view)

    def search(self, problem, threshold):
        frontier = LifoQueue()
        frontier.put(IDAStarNode(problem.init, h=self.w * self.heuristic(problem.init, problem.goal), threshold=threshold))
        reached = set()
        self.reset_expanded()

        while frontier:
            n = frontier.get_nowait()
            if n.g + n.h > n.threshold:
                return n  # Found a node that exceeds threshold, potentially leads to solution

            if problem.isGoal(n.state):
                return self.extract_solution(n)  # Found the goal!

            for a, s, cost in problem.getSuccessors(n.state):
                if s not in reached:
                    self.update_expanded(s)
                    reached.add(s)
                    new_g = n.g + cost
                    new_h = self.w * self.heuristic(s, problem.goal)
                    frontier.put(IDAStarNode(s, n, a, new_g, new_h, min(n.threshold, new_g + new_h)))

        return None  # No solution found

    def solve(self, problem):
        while True:
            result = self.search(problem, self.cutoff)
            if result is None:
                return None  # No solution found even after increasing the threshold
            elif isinstance(result, IDAStarNode):
                self.cutoff = result.threshold  # Update threshold for next iteration
            else:
                return self.extract_solution(result)  # Found the goal!