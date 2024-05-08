import folium
import osmnx as ox
import random
import time
import electric_vehicle as ev
import numpy as np
import webbrowser
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from sklearn.neighbors import BallTree
from geopy.exc import GeocoderTimedOut
import tkinter as tk
import customtkinter as ctk
import tkinter.messagebox
"""
Questo modulo fornisce un'interfaccia grafica per la simulazione di un veicolo elettrico che si muove in una rete stradale.

Il modulo utilizza OpenStreetMap per generare la rete stradale e simula il movimento di un veicolo elettrico attraverso di essa. Fornisce anche un'interfaccia grafica per visualizzare la simulazione e interagire con essa.

Il modulo dipende dai moduli 'folium', 'osmnx', 'random', 'time', 'electric_vehicle', 'numpy', 'webbrowser', 'folium.plugins', 'geopy.geocoders', 'sklearn.neighbors', 'geopy.exc', 'tkinter', 'customtkinter' e 'tkinter.messagebox' per funzionare correttamente.

Variabili:
    electric_vehicle_data (dict): Un dizionario che mappa i nomi dei modelli di veicoli elettrici alle loro specifiche.
"""

electric_vehicle_data = {
    "Tesla Model 3 Standard Range Plus": {
        "battery_capacity_kWh": 54,
        "electric_constant": 0.05
    },
    "MINI Electric": {
        "battery_capacity_kWh": 32.6,
        "electric_constant": 0.055
    },
    "Renault Twizy": {
        "battery_capacity_kWh": 6.1,
        "electric_constant": 0.07
    },
    "Renault Twingo Electric": {
        "battery_capacity_kWh": 22,
        "electric_constant": 0.06
    },
    "Fiat 500e": {
        "battery_capacity_kWh": 42,
        "electric_constant": 0.055
    }
}

def generate_osm_graph(location, num_charging_stations = 0):
    """
    Genera un grafo stradale da OpenStreetMap.

    Questa funzione scarica i dati della rete stradale da OpenStreetMap e li converte in un grafo NetworkX. Aggiunge anche le velocità degli archi,
    i tempi di percorrenza e le lunghezze degli archi al grafo. Se non viene specificato un numero di stazioni di ricarica, il 30% dei nodi viene impostato come stazioni di ricarica.

    Args:
        location (str): La località da cui scaricare i dati della rete stradale.
        num_charging_stations (int, optional): Il numero di stazioni di ricarica da aggiungere al grafo. Default a None.

    Returns:
        ox.Graph: Il grafo della rete stradale.
        list: Una lista degli indici delle stazioni di ricarica nel grafo.
    """
    # Genera un grafo da OpenStreetMap
    G = ox.graph_from_place(location, network_type = 'drive')  # Scarica i dati della rete stradale da OSM
    G = ox.routing.add_edge_speeds(G) # Aggiungi velocità agli archi in km/h 'speed_kph'
    G = ox.routing.add_edge_travel_times(G) # Aggiungi tempi di percorrenza agli archi in secondi s 'travel_time'
    G = ox.distance.add_edge_lengths(G) # Aggiungi lunghezze degli archi in metri m 'length'
    G = ox.utils_graph.convert.to_digraph(G, weight = "travel_time") # Converte MultiDiGraph in DiGraph
    G = G.to_undirected() # Converte in un grafo non diretto

    all_nodes = list(G.nodes)
    if num_charging_stations is None or num_charging_stations <= 0: # Imposta il 30% dei nodi come stazioni di ricarica se non viene specificato il numero
        num_charging_stations = int(len(all_nodes) * 0.3)
    charging_stations = random.sample(all_nodes, num_charging_stations)
    for node in charging_stations:
        G.nodes[node]['charging_station'] = True
    return G, charging_stations

def draw_solution_on_map(graph, solution, start_node, end_node, charging_stations):
    """
    Disegna la soluzione del percorso su una mappa interattiva.

    Questa funzione utilizza la libreria folium per creare una mappa interattiva. Il percorso della soluzione viene disegnato sulla mappa,
    e vengono aggiunti marcatori per il nodo di partenza, il nodo di arrivo e le stazioni di ricarica.

    Args:
        graph (networkx.Graph): Il grafo in cui è stato trovato il percorso.
        solution (list): La soluzione del percorso, come lista di coppie di nodi.
        start_node (int): L'indice del nodo di partenza nel grafo.
        end_node (int): L'indice del nodo di arrivo nel grafo.
        charging_stations (list): Una lista degli indici delle stazioni di ricarica nel grafo.

    Returns:
        folium.Map: Una mappa interattiva con il percorso disegnato su di essa e marcatori per il nodo di partenza, il nodo di arrivo e le stazioni di ricarica.
    """
    start_node_coordinates = [graph.nodes[start_node]['y'], graph.nodes[start_node]['x']] # Crea una mappa centrata sulla posizione media dei nodi
    m = folium.Map(location=start_node_coordinates,tiles='CartoDB Positron', zoom_start=14) # Crea una mappa con folium
    for action in solution: # Disegna il percorso sulla mappa
        start_node_data = graph.nodes[action[0]]
        end_node_data = graph.nodes[action[1]]
        start_pos = [start_node_data['y'], start_node_data['x']]
        end_pos = [end_node_data['y'], end_node_data['x']]
        folium.PolyLine(locations=[start_pos, end_pos], color="red", weight=2.5, opacity=1).add_to(m)
    # Aggiungi marcatori per il nodo di partenza e di destinazione
    folium.Marker(location=[graph.nodes[start_node]['y'], graph.nodes[start_node]['x']], popup='Start', icon=folium.Icon(color='blue',prefix='fa',icon='car')).add_to(m)
    folium.Marker(location=[graph.nodes[end_node]['y'], graph.nodes[end_node]['x']], popup='End', icon=folium.Icon(color='red', prefix='fa', icon='map-pin')).add_to(m)
    marker_cluster = MarkerCluster().add_to(m) # Crea un oggetto MarkerCluster
    for station in charging_stations: # Aggiungi marcatori per tutte le stazioni di ricarica
        station_data = graph.nodes[station]
        folium.Marker(location=[station_data['y'], station_data['x']], popup=f'Charging Station: {station}', icon=folium.Icon(color='green', prefix='fa', icon='bolt')).add_to(marker_cluster)
    return m

def nearest_existing_node(G, lat, lon):
    """
    Trova il nodo più vicino nel grafo rispetto a un punto di riferimento specificato.

    Questa funzione utilizza un albero di ricerca per trovare il nodo più vicino nel grafo rispetto a un punto di riferimento specificato in termini di latitudine e longitudine.

    Args:
        G (networkx.Graph): Il grafo in cui cercare il nodo.
        lat (float): La latitudine del punto di riferimento.
        lon (float): La longitudine del punto di riferimento.

    Returns:
        int: L'indice del nodo più vicino nel grafo.
    """
    nodes = np.array([[data['y'], data['x']] for _, data in G.nodes(data=True)])
    tree = BallTree(nodes, leaf_size=2)
    index = tree.query([[lat, lon]], k=1, return_distance=False)[0][0]
    return list(G.nodes)[index]

# Funzione per verificare che il luogo inserito esista
def get_coordinates(geolocator, location):
    """
    Ottiene le coordinate geografiche di una località utilizzando un geolocalizzatore.

    Questa funzione utilizza un geolocalizzatore per ottenere le coordinate geografiche di una località. Se la località non esiste, la funzione restituisce None.

    Args:
        geolocator (geopy.geocoders.Nominatim): Il geolocalizzatore da utilizzare per ottenere le coordinate.
        location (str): La località di cui ottenere le coordinate.

    Returns:
        geopy.location.Location: L'oggetto Location con le coordinate della località, o None se la località non esiste.
    """
    location = location.capitalize()
    try:
        result = geolocator.geocode(location)
        if result is not None:
            return result  # Restituisce l'oggetto Location, non solo l'indirizzo
    except GeocoderTimedOut:
        print("Errore di timeout del geolocalizzatore. Per favore, riprova.")
    print("Il luogo inserito non esiste. Per favore, riprova.")
    return None

def print_solution(G, solution, electric_vehicle):
    """
    Stampa la soluzione di un percorso e le informazioni relative al veicolo elettrico.

    Questa funzione stampa la soluzione di un percorso, il numero di azioni nel percorso, le informazioni sulla batteria del veicolo elettrico, il numero di volte che il veicolo è stato ricaricato, l'energia ricaricata, il tempo di viaggio e la distanza percorsa.

    Args:
        G (networkx.Graph): Il grafo in cui è stato trovato il percorso.
        solution (list): La soluzione del percorso, come lista di azioni.
        electric_vehicle (ElectricVehicle): Il veicolo elettrico utilizzato per il percorso.
    """
    distance = 0
    for i, j in solution:
        edge = G.edges[i, j]
        distance += edge.get('length', 10)
    print("Soluzione:", solution)
    print("Percorso trovato con", len(solution), "azioni")
    print("Batteria rimanente: {:.2f} kWh, Macchina ricaricata {} volte, Energia ricaricata: {} kWh".format(electric_vehicle.battery, electric_vehicle.recharge, electric_vehicle.energy_recharged))    
    print("Tempo trascorso: {:.2f} ore. Distanza percorsa: {:.2f} km".format(electric_vehicle.travel_time / 3600, distance / 1000))

def main(battery_at_goal_percent, location_city, start_coordinates, end_coordinates, battery_capacity, electric_constant, temperature):
    """
    Funzione principale del programma che gestisce la simulazione del percorso di un veicolo elettrico.

    Questa funzione crea un veicolo elettrico, genera un grafo stradale da OpenStreetMap, trova il nodo più vicino alle coordinate di partenza e di arrivo,
    esegue la ricerca del percorso, stampa il tempo di ricerca e, se esiste una soluzione, stampa la soluzione, disegna la soluzione su una mappa e apre la mappa in un browser web.

    Args:
        battery_at_goal_percent (float): La percentuale di batteria desiderata alla fine del percorso.
        location_city (str): La città in cui si trova il percorso.
        start_coordinates (tuple): Le coordinate del punto di partenza del percorso.
        end_coordinates (tuple): Le coordinate del punto di arrivo del percorso.
        battery_capacity (float): La capacità della batteria del veicolo elettrico.
        electric_constant (float): La costante elettrica del veicolo elettrico.
    """
    electric_vehicle = ev.ElectricVehicle(battery_capacity, battery_capacity, battery_capacity * battery_at_goal_percent / 100, electric_constant)

    print("Scarico la mappa...")
    G, charging_stations = generate_osm_graph(location_city) # Genera il grafo e le stazioni di ricarica, se non si inserisce il numero di stazioni rende il 40% dei nodi stazioni
    start_node = nearest_existing_node(G, start_coordinates.latitude, start_coordinates.longitude)
    end_node = nearest_existing_node(G, end_coordinates.latitude, end_coordinates.longitude)

    start_time = time.time()
    solution = ev.ElectricVehicle.adaptive_search(electric_vehicle, G, start_node, end_node, temperature)
    end_time = time.time()
    print("Tempo di ricerca:", end_time - start_time, "secondi")

    if solution:
        print_solution(G, solution, electric_vehicle)
        m = draw_solution_on_map(G, solution, start_node, end_node, charging_stations)
        m.save("path.html")
        webbrowser.open('path.html')
    else:
        print("No solution found")

# GUI code
def change_mode():
    """
    Cambia la modalità di visualizzazione dell'interfaccia utente.

    Questa funzione cambia la modalità di visualizzazione dell'interfaccia utente tra "dark" e "light" in base al valore della variabile `var`.
    """
    ctk.set_appearance_mode("dark" if var.get() else "light")

def run_algorithm():
    """
    Esegue l'algoritmo di ricerca del percorso.

    Questa funzione raccoglie i dati di input dall'interfaccia utente, verifica la validità degli input, e poi esegue l'algoritmo di ricerca del percorso.
    Se gli input non sono validi, mostra un messaggio di errore. Altrimenti, esegue l'algoritmo e visualizza il risultato.
    """
    battery_at_goal_percent = int(entry_battery.get())
    location_city = entry_location.get()
    start_location = entry_start.get()
    end_location = entry_end.get()
    temperature = int(entry_temperature.get())
    geolocator = Nominatim(user_agent="bsGeocoder")
    start_coordinates = get_coordinates(geolocator, start_location)
    end_coordinates = get_coordinates(geolocator, end_location)
    if start_coordinates is None or end_coordinates is None or location_city is None or battery_at_goal_percent is None:
        tkinter.messagebox.showerror("Error", "Invalid input. Please try again.")
    else:
        selected_vehicle = vehicle_combobox.get()
        vehicle_data = electric_vehicle_data[selected_vehicle]
        battery_capacity = vehicle_data["battery_capacity_kWh"]
        electric_constant = vehicle_data["electric_constant"]
        main(battery_at_goal_percent, location_city, start_coordinates, end_coordinates, battery_capacity, electric_constant, temperature)

# Creazione della finestra principale
root = ctk.CTk()
root.title("EVOPT-Maps")

# Impostazione delle dimensioni e della posizione della finestra
window_width = 800
window_height = 600
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
position_top = int(screen_height / 2 - window_height / 2)
position_left = int(screen_width / 2 - window_width / 2)
root.geometry(f"{window_width}x{window_height}+{position_left}+{position_top}")

# Impedire il ridimensionamento della finestra
root.resizable(False, False)

# Creazione del pulsante per cambiare la modalità di visualizzazione
var = tk.IntVar()
checkbutton = ctk.CTkSwitch(root, text="Tema Scuro", variable=var, command = change_mode)
checkbutton.pack(anchor='ne', padx=10, pady=10)

# Creazione dei widget per l'interfaccia utente: titolo
welcome_label = ctk.CTkLabel(root, text="Benvenuto in EVOPT Maps", font=("Helvetica", 24))
welcome_label.pack(pady=20)
# Creazione dei widget per l'interfaccia utente: veicolo
label_vehicle = ctk.CTkLabel(root, text="Seleziona un veicolo elettrico:", font=("Helvetica", 14))
label_vehicle.pack(pady=2)
# Creazione dei widget per l'interfaccia utente: combo box veicolo
vehicle_var = ctk.StringVar(value=list(electric_vehicle_data.keys())[0])
vehicle_combobox = ctk.CTkComboBox(root, values=list(electric_vehicle_data.keys()), variable=vehicle_var)
vehicle_combobox.pack(pady=1)
# Creazione dei widget per l'interfaccia utente: percentuale di batteria
label_battery = ctk.CTkLabel(root, text="Inserisci la percentuale di batteria minima di arrivo:", font=("Helvetica", 14))
label_battery.pack(pady=1)
entry_battery = ctk.CTkEntry(root)
entry_battery.pack(pady=1)
# Creazione dei widget per l'interfaccia utente: mappa da scaricare
label_location = ctk.CTkLabel(root, text="Inserisci la città o il paese:", font=("Helvetica", 14))
label_location.pack(pady=1)
entry_location = ctk.CTkEntry(root)
entry_location.pack(pady=1)
# Creazione dei widget per l'interfaccia utente: luogo di partenza
label_start = ctk.CTkLabel(root, text="Inserisci il luogo di partenza:", font=("Helvetica", 14))
label_start.pack(pady=1)
entry_start = ctk.CTkEntry(root)
entry_start.pack(pady=1)
# Creazione dei widget per l'interfaccia utente: luogo di destinazione
label_end = ctk.CTkLabel(root, text="Inserisci il luogo di destinazione:", font=("Helvetica", 14))
label_end.pack(pady=1)
entry_end = ctk.CTkEntry(root)
entry_end.pack(pady=1)
# Creazione dei widget per l'interfaccia utente: temperatura
label_temperature = ctk.CTkLabel(root, text="temp°C:", font=("Helvetica", 14))
label_temperature.place(x=158, y=112)
entry_temperature = ctk.CTkEntry(root)
entry_temperature.insert(0, "20")
entry_temperature.place(x=158, y=142)
entry_temperature.configure(font=("Helvetica", 14), width=35)
# Creazione dei widget per l'interfaccia utente: pulsante esegui
button_run = ctk.CTkButton(root, text="Esegui", command=run_algorithm)
button_run.pack(pady=15)

# Avvio del loop principale dell'interfaccia utente
root.mainloop()
