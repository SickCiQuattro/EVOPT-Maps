## What is this?
This repository contains an implementation of a search problem and three basic search algorithms for single-agent deterministic problem-solving: Depth-First-Search, Breath-First-Search, and AStar. To make things concrete, we also provide a path-finding problem as a specific instance of a search problem and show how to solve it using the three aforementioned algorithms with Pygame, a general-purpose library for developing 2D and 3D animations in Python.

The visualizer allows the user to set up a path-finding problem graphically by selecting the starting and ending points for the path and obstacles on a customizable square grid. The resulting map can then be saved to a file.

While this is still a work in progress, we believe it can be a valuable resource for seeing search algorithms in action. We've taken care to ensure a clear separation between a generic search problem, a path-finding problem, and the visualizer.

To see it in action, simply execute the following command:

```python3 path_finding_gui.py -f maps/map_1.json```

and press the spacebar to run AStar on that map. Unless you're using a computer from the Middle Ages, you should be able to see the path in purple and the expanded nodes by the algorithm in red almost instantaneously. More details about the execution will also be available in the terminal's standard output.

## What do you need?
You'll need Python 3, Pygame (which can be installed using pip or pip3), and Click (also installable via pip or pip3). If we've forgotten anything, please let us know.