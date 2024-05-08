import heuristics as h
from ASTAR import AStar
from path_finding import PathFinding
"""
Questo modulo definisce la classe ElectricVehicle, che rappresenta un veicolo elettrico in un sistema di navigazione.

La classe ElectricVehicle tiene traccia delle informazioni relative al veicolo, come la capacità della batteria, il livello attuale della batteria, il livello minimo di batteria richiesto, la costante elettrica del veicolo, l'energia ricaricata e il tempo di viaggio totale.

Il modulo fornisce anche metodi per calcolare l'energia consumata per un dato percorso, aggiornare il percorso del veicolo e il tempo di viaggio, e calcolare l'energia necessaria per ricaricare il veicolo.

Questo modulo dipende dai moduli 'heuristics', 'ASTAR' e 'path_finding' per funzionare correttamente.

Classes:
    ElectricVehicle: Rappresenta un veicolo elettrico in un sistema di navigazione.
"""

class ElectricVehicle:
    """
    Classe che rappresenta un veicolo elettrico.

    Args:
        battery_capacity (int, optional): La capacità massima della batteria. Default è 100.
        battery (int, optional): Il livello attuale della batteria. Default è 100.
        min_battery (int, optional): Il livello minimo di batteria richiesto. Default è 20.
        electric_constant (float, optional): La costante elettrica del veicolo. Default è 0.06.
        energy_recharged (list, optional): Una lista delle energie ricaricate. Default è una lista vuota.
        travel_time (int, optional): Il tempo di viaggio totale. Default è 0.
    """
    def __init__(self, battery_capacity = 100, battery = 100, min_battery = 20, electric_constant = 0.06, energy_recharged = None, travel_time = 0):
        self.battery_capacity = battery_capacity
        self.battery = battery
        self.min_battery = min_battery
        self.electric_constant = electric_constant
        self.recharge = 0
        self.energy_recharged = energy_recharged if energy_recharged is not None else []
        self.travel_time = travel_time

    def calculate_energy_consumed(self, solution, graph, ambient_temperature):
        """
        Calcola l'energia consumata in kWh e il tempo complessivo per un dato percorso.

        Args:
            solution (list): Il percorso da calcolare. Ogni elemento è una coppia di nodi.
            graph (Graph): Il grafo che rappresenta il percorso.
            ambient_temperature (float): La temperatura ambiente.

        Returns:
            tuple: L'energia consumata (float) e il tempo impiegato (int).
        """
        energy_consumed = time = 0
        for i, j in solution:
            edge = graph.edges[i, j]
            distance = edge.get('length', 10)
            speed = edge.get('speed_kph', 50)
            energy_consumed += self.electric_constant * (distance / 1000) * speed / ambient_temperature
            time += edge.get('travel_time', 10)
        return energy_consumed, time
    
    def update_path(self, solution, energy_consumed, time):
        """
        Aggiorna il percorso, il tempo di viaggio e il livello della batteria del veicolo.

        Args:
            solution (list): Il nuovo percorso. Ogni elemento è una coppia di nodi.
            energy_consumed (float): L'energia consumata durante il percorso.
            time (int): Il tempo impiegato per il percorso.
        """
        self.path += solution
        self.travel_time += time
        self.battery -= energy_consumed

    def calculate_recharge_needed(self, charging_station_start, goal, graph, ambient_temperature, energy_consumed = 0):
        """
        Calcola l'energia necessaria per ricaricare il veicolo elettrico in modo da raggiungere l'obiettivo dal punto di ricarica.

        Questo metodo considera la distanza tra la stazione di ricarica e l'obiettivo, la temperatura ambiente e l'energia già consumata.

        Args:
            charging_station_start (int): Il nodo di partenza della stazione di ricarica.
            goal (int): Il nodo di arrivo.
            graph (Graph): Il grafo che rappresenta il percorso.
            ambient_temperature (float): La temperatura ambiente.
            energy_consumed (float, optional): L'energia già consumata. Default a 0.

        Returns:
            float: L'energia necessaria per la ricarica, considerando un margine di sicurezza del 10%.
        """
        if energy_consumed <= 0:
            distance = h.euclidean_distance(charging_station_start, goal, graph)
            energy_needed = self.min_battery + (self.electric_constant * distance * 60 / ambient_temperature) * 1.1 # margine di sicurezza del 10%
        else:
            energy_needed = self.min_battery + energy_consumed * 1.1 # margine di sicurezza del 10%

        if self.battery >= self.min_battery and energy_needed + self.battery <= self.battery_capacity:
            print("Energia necessaria: ", energy_needed)
            # return self.battery_capacity - self.battery
            return energy_needed
        else:
            print("Energia totale necessaria: ", energy_needed)
            return self.battery_capacity - self.battery

    def nearest_charging_station(self, graph, start, goal, solution, ambient_temperature):
        """
        Trova la stazione di ricarica più vicina che può essere raggiunta con l'energia rimanente nella batteria.

        Questo metodo considera tutte le stazioni di ricarica nel grafo e restituisce quella più vicina che può essere raggiunta con l'energia rimanente.

        Args:
            graph (Graph): Il grafo che rappresenta il percorso.
            start (int): Il nodo di partenza.
            goal (int): Il nodo di arrivo.
            solution (list): Il percorso attuale.
            ambient_temperature (float): La temperatura ambiente.

        Returns:
            int: Il nodo della stazione di ricarica più vicina che può essere raggiunta con l'energia rimanente.
        """
        # Ottieni tutte le stazioni di ricarica
        charging_stations = [node for node in graph.nodes() if graph.nodes[node].get('charging_station', False)]
        percent = 1.0 # Parte dal 100%
        while percent > 0.2:
            percent -= 0.1 # Riduce del 10% ad ogni iterazione
            distanza_minima = float('inf')
            best_station = None
            new_start = start
            nodo_raggio = goal
            sw = False
            distance = speed = energy_consumed = distance_radius = raggio = speed_tot = count = 0
            for i, j in solution: # Calcola l'energia consumata nel percorso migliore
                edge = graph.edges[i, j]
                distance = edge.get('length', 10)
                if not sw:
                    speed = edge.get('speed_kph', 50)
                    speed_tot += speed
                    count += 1
                    energy_consumed += self.electric_constant * (distance / 1000) * speed / ambient_temperature
                    if energy_consumed >= self.battery * percent: # Fino a quando l'energia non raggiunge la % richiesta
                        new_start = j # Aggiorna il nuovo nodo di partenza
                        raggio = abs(self.battery - energy_consumed) * ambient_temperature / (self.electric_constant * speed * speed_tot / count)
                        print("Raggio: ", raggio)
                        sw = True
                if sw: # Calcola la distanza dal nuovo nodo di partenza al nodo in solution massimo nell'ampiezza del raggio
                    distance_radius += distance / 1000
                    print("Distanza: ", distance_radius)
                    if distance_radius >= raggio:
                        nodo_raggio = j
                        break

        # while percent > 0.2:
        #     percent -= 0.1 # Riduce del 10% ad ogni iterazione
        #     print("Percentuale: ", percent)
        #     distanza_minima = float('inf')
        #     best_station = None
        #     new_start = start
        #     distance = speed = energy_consumed = speed_tot = count = 0
        #     for i, j in solution: # Calcola l'energia consumata nel percorso migliore
        #         edge = graph.edges[i, j]
        #         distance = edge.get('length', 10)
        #         speed = edge.get('speed_kph', 50)
        #         speed_tot += speed
        #         count += 1
        #         energy_consumed += self.electric_constant * (distance / 1000) * speed / ambient_temperature
        #         if energy_consumed >= self.battery * percent: # Fino a quando l'energia non raggiunge la % richiesta
        #             new_start = j # Aggiorna il nuovo nodo di partenza
        #             break
        #     raggio = abs(self.battery - energy_consumed) * ambient_temperature / (self.electric_constant * speed_tot / count)
        #     print("Raggio: ", raggio)

            for station in charging_stations: # Trova la stazione di ricarica migliore
                start_dist = h.euclidean_distance(new_start, station, graph) # come differenza tra il nuovo nodo di partenza e la stazione
                # goal_dist = h.euclidean_distance(goal, station, graph)
                goal_dist = h.euclidean_distance(nodo_raggio, station, graph) # e il nodo in solution massimo nell'ampiezza del raggio e la stazione
                if start_dist > raggio: # Se la stazione è fuori dal raggio (troppo distante), continua
                    continue
                if start_dist + goal_dist < distanza_minima:
                    print("ci entri?")
                    distanza_minima = start_dist + goal_dist
                    best_station = station
            if best_station is None:
                continue

            problem = PathFinding(graph, start, best_station)
            astar = AStar(graph, h.euclidean_distance, view=True)
            solution_charging = astar.solve(problem)
            if solution_charging is None:
                continue
            time = 0
            energy_consumed, time = self.calculate_energy_consumed(solution_charging, graph, ambient_temperature)
            if energy_consumed >= self.battery:
                print("non hai mai abbastanza energia")
                continue
            return best_station, solution_charging, energy_consumed, time
        return None, None, None, None

    def adaptive_search(self, graph, start, goal, ambient_temperature):
        """
        Trova la stazione di ricarica più vicina che può essere raggiunta con l'energia rimanente nella batteria.

        Questo metodo esamina tutte le stazioni di ricarica nel grafo e restituisce il nodo della stazione di ricarica più vicina che può essere raggiunta con l'energia rimanente nella batteria. Se non esiste una stazione di ricarica raggiungibile, il metodo solleva un'eccezione.

        Il metodo modifica l'attributo `self.energy_recharged` per riflettere l'energia ricaricata alla stazione di ricarica.

        Args:
            graph (Graph): Il grafo che rappresenta il percorso. Deve contenere informazioni sulle stazioni di ricarica.
            start (int): Il nodo di partenza.
            goal (int): Il nodo di arrivo.
            solution (list): Il percorso attuale. Ogni elemento è una coppia di nodi.
            ambient_temperature (float): La temperatura ambiente in gradi Celsius.

        Returns:
            int: Il nodo della stazione di ricarica più vicina che può essere raggiunta con l'energia rimanente.

        Raises:
            Exception: Se non esiste una stazione di ricarica raggiungibile con l'energia rimanente.

        Side Effects:
            Modifica `self.energy_recharged` per riflettere l'energia ricaricata alla stazione di ricarica.
        """
        self.path = []
        while True:
            problem = PathFinding(graph, start, goal) # Inizializza il problema di ricerca
            astar = AStar(graph, h.euclidean_distance, view = True) # Inizializza l'algoritmo di ricerca A*
            solution = astar.solve(problem)
            if solution is None:
                raise Exception("Percorso completo non trovato")
        
            # Calcola la distanza, la velocità e l'energia consumata
            energy_consumed, time = self.calculate_energy_consumed(solution, graph, ambient_temperature)
            energy_start_goal = energy_consumed

            # Se l'energia consumata è inferiore all'energia necessaria, restituisci il percorso
            if energy_consumed < self.battery - self.min_battery:
                # Aggiungi il percorso alla soluzione
                self.update_path(solution, energy_consumed, time)
                return self.path
                
            # Altrimenti, cerca la stazione di ricarica migliore
            charging_station_start, solution, energy_consumed, time = self.nearest_charging_station(graph, start, goal, solution, ambient_temperature)
            if charging_station_start is None:
                raise Exception("Stazione di ricarica non trovata")
            if solution is None:
                raise Exception("Percorso stazione non trovato")
              
            # Aggiungi il percorso alla soluzione
            self.update_path(solution, energy_consumed, time)

            # Calcolo intelligente della ricarica
            recharge_needed = self.calculate_recharge_needed(charging_station_start, goal, graph, ambient_temperature, energy_start_goal - energy_consumed)
            self.energy_recharged.append(recharge_needed)
            self.travel_time += (recharge_needed) / 22 * 3600
            self.battery = recharge_needed   
            self.recharge += 1
            graph.nodes[charging_station_start]['charging_station'] = False

            # Continua la ricerca
            start = charging_station_start
            