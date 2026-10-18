# EVOPT-Maps

EVOPT Maps is a project developed as a university assignment for the "Intelligent Systems" course. The project leverages the osmnx library to implement real-world streets and simulate the journey of an electric vehicle.

## Introduction

EVOPT Maps aims to develop a system for electric vehicle charging. It provides a user-friendly interface for users to automatically locate and reserve charging stations. The project uses a search algorithm to find the most efficient route for the electric vehicle, considering factors such as distance, time, speed, and availability of charging stations. 

The search algorithm was chosen for several reasons. Firstly, it allows for the consideration of multiple factors in route selection, providing a more comprehensive solution than simple distance-based algorithms. Secondly, it is highly adaptable and can be easily adjusted to account for changes in road conditions or vehicle parameters.

## Features

- Downloads real-world maps with accurate information.
- Automates the process of searching and locating charging stations.
- Allows users to specify the desired battery percentage at the end of the journey.

## Stato del progetto

Il vecchio codice (A* + GUI tkinter) è nel branch `legacy`. `main` è in riscrittura: nucleo di routing in `evopt/`, interfaccia web in arrivo.

## Setup

```bash
uv sync
uv run pytest
```

## Uso (libreria)

```python
from evopt.graph import load_graph, nearest_node
from evopt.router import plan_route
from evopt.vehicle import VEHICLES

G = load_graph("Pieve Emanuele, Italy")  # le stazioni sono nodi con attributo 'charger_kw'
route = plan_route(G, start, goal, VEHICLES["Fiat 500e"], temp_c=5, min_soc=0.1)
```

## UI examples

Here are some previews of the user interface:

![GUI preview](https://github.com/PasticciniTeams/EVOPT-Maps/blob/main/example/gui_example.png)
![MAPS preview](https://github.com/PasticciniTeams/EVOPT-Maps/blob/main/example/maps_example.png)

## Contributors

- [Camossi Filippo](https://github.com/SickCiQuattro)
- [Cioli Daniele](https://github.com/Profect99)

## Note

[This file](https://github.com/PasticciniTeams/EVOPT-Maps/blob/old-algorithm/Search/electric_vehicle.py), originating from a previous branch, illustrates a modified version of the old A* based search algorithm 

## License

All resources used within the project are free license!
