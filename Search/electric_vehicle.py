import heuristics as h
from ASTAR import AStar
from path_finding import PathFinding

class ElectricVehicle:
    """Classe che rappresenta un veicolo elettrico.

    Args:
        battery_capacity (int): La capacità massima della batteria.
        battery (int): Il livello attuale della batteria.
        min_battery (int): Il livello minimo di batteria richiesto.
        electric_constant (float): La costante elettrica del veicolo.
        recharge (int): Numero di ricariche.
        energy_recharged (list): Una lista delle energie ricaricate.
        travel_time (int): Il tempo di viaggio totale.
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
        """Calcola l'energia consumata per un dato percorso.

        Args:
            solution (list): Il percorso da calcolare.
            graph (Graph): Il grafo che rappresenta il percorso.
            ambient_temperature (float): La temperatura ambiente.

        Returns:
            tuple: L'energia consumata e il tempo impiegato.
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
        """Aggiorna il percorso, il tempo di viaggio e il livello della batteria.

        Args:
            solution (list): Il percorso da aggiornare.
            energy_consumed (float): L'energia consumata durante il percorso.
            time (int): Il tempo impiegato per il percorso.
        """
        self.path += solution
        self.travel_time += time
        self.battery -= energy_consumed

    def calculate_recharge_needed(self, charging_station_start, goal, graph, ambient_temperature, energy_consumed = 0):
        """Calcola il livello di ricarica necessario in modo intelligente.

        Args:
            charging_station_start (int): Il nodo di partenza della stazione di ricarica.
            goal (int): Il nodo di arrivo.
            graph (Graph): Il grafo che rappresenta il percorso.
            ambient_temperature (float): La temperatura ambiente.
            energy_consumed (float, optional): L'energia consumata. Default a 0.

        Returns:
            float: L'energia necessaria per la ricarica.
        """
        if energy_consumed <= 0:
            distance = h.euclidean_distance(charging_station_start, goal, graph)
            energy_needed = self.min_battery + (self.electric_constant * distance * 60 / ambient_temperature) * 1.2 # margine di sicurezza del 20%
        else:
            energy_needed = self.min_battery + energy_consumed * 1.2 # margine di sicurezza del 20%
        if energy_needed >= self.battery_capacity or energy_needed + self.battery >= self.battery_capacity:
            return self.battery_capacity - self.battery
        else:
            return self.battery_capacity - self.battery
            # return energy_needed

    def nearest_charging_station(self, graph, start, goal, solution, ambient_temperature):
        """Trova la stazione di ricarica più vicina.

        Args:
            graph (Graph): Il grafo che rappresenta il percorso.
            start (int): Il nodo di partenza.
            goal (int): Il nodo di arrivo.
            solution (list): Il percorso attuale.
            ambient_temperature (float): La temperatura ambiente.

        Returns:
            int: Il nodo della stazione di ricarica più vicina.
        """
        # Ottieni tutte le stazioni di ricarica
        charging_stations = [node for node in graph.nodes() if graph.nodes[node].get('charging_station', False)]
        percent = 1 # Parte dal 100%
        while percent > 0:
            percent -= 0.1 # Riduce del 10% ad ogni iterazione
            distanza_minima = float('inf')
            best_station = None
            new_start = start
            distance = speed = energy_consumed = 0
            for i, j in solution: # Calcola l'energia consumata nel percorso migliore
                edge = graph.edges[i, j]
                distance = edge.get('length', 10)
                speed = edge.get('speed_kph', 50)
                energy_consumed += self.electric_constant * (distance / 1000) * speed / ambient_temperature
                if energy_consumed >= self.battery * percent: # Fino a quando l'energia non raggiunge la % richiesta
                    new_start = j # Aggiorna il nuovo nodo di partenza
                    break
            raggio = abs(self.battery - energy_consumed) * ambient_temperature / (self.electric_constant * speed)

            for station in charging_stations: # Trova la stazione di ricarica migliore
                start_dist = h.euclidean_distance(new_start, station, graph)
                goal_dist = h.euclidean_distance(goal, station, graph)
                if start_dist > raggio: # Se la stazione è fuori dal raggio (troppo distante), continua
                    continue
                if start_dist + goal_dist < distanza_minima:
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
            energy_consumed, time = self.calculate_energy_consumed(solution, graph, ambient_temperature)
            if energy_consumed >= self.battery:
                continue
            return best_station, solution_charging, energy_consumed, time
        return None, None, None, None

    def adaptive_search(self, graph, start, goal, ambient_temperature):
        """Esegue una ricerca adattiva per trovare il percorso da un nodo di partenza a un nodo obiettivo.

        Questo metodo utilizza l'algoritmo A* per trovare il percorso, calcola l'energia consumata lungo il percorso e, se necessario, trova la stazione di ricarica più vicina e calcola l'energia necessaria per la ricarica.

        Args:
            graph (Graph): Il grafo su cui eseguire la ricerca.
            start (int): Il nodo di partenza.
            goal (int): Il nodo obiettivo.
            ambient_temperature (float): La temperatura ambiente.

        Returns:
            list: Il percorso dal nodo di partenza al nodo obiettivo.

        Raises:
            Exception: Se non è possibile trovare un percorso completo o una stazione di ricarica.
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
            