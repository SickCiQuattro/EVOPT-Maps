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

## Avvio

```bash
uv sync
echo 'OCM_API_KEY=la_tua_chiave' > .env   # facoltativa: completa la potenza delle stazioni (openchargemap.org)
uv run --env-file .env uvicorn evopt.api:app
```

Apri http://127.0.0.1:8000. Il primo piano per una nuova città scarica le strade da OpenStreetMap e può richiedere alcuni minuti; poi grafo e stazioni restano in `cache/` (30 e 7 giorni).

![Interfaccia web](example/web.png)

Test e lint: `uv run pytest` e `uv run ruff check .`.

## Uso come libreria

```python
from evopt.data import load_network
from evopt.graph import nearest_node
from evopt.router import plan_route
from evopt.vehicle import VEHICLES

G = load_network("Pieve Emanuele, Italy")  # strade + stazioni (OSM, più Open Charge Map se c'è la chiave)
start, goal = nearest_node(G, 45.35, 9.17), nearest_node(G, 45.33, 9.15)
route = plan_route(G, start, goal, VEHICLES["Renault Twizy"], temp_c=-10, start_soc=0.15, min_soc=0.1)
```

## Come funziona

- **Energia:** resistenza al rotolamento e aerodinamica per ogni tratto, più servizi di bordo e climatizzazione in funzione della temperatura.
- **Percorso:** Dijkstra sul tempo su un grafo ridotto di partenza, arrivo e stazioni, con la carica discretizzata all'1%.
- **Limiti:** niente traffico, quota o disponibilità in tempo reale; ricarica a potenza costante; 22 kW dove la potenza della stazione è ignota.

## Contributors

- [Camossi Filippo](https://github.com/SickCiQuattro)
- [Cioli Daniele](https://github.com/Profect99)

## Note

[This file](https://github.com/PasticciniTeams/EVOPT-Maps/blob/old-algorithm/Search/electric_vehicle.py), originating from a previous branch, illustrates a modified version of the old A* based search algorithm 

## License

All resources used within the project are free license!
