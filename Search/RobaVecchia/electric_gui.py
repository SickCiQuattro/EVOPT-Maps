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

# Funzione per generare un grafo da OpenStreetMap
def generate_osm_graph(location, num_charging_stations):
    # Genera un grafo da OpenStreetMap
    G = ox.graph_from_place(location, network_type='drive')  # Scarica i dati della rete stradale da OSM
    G = ox.routing.add_edge_speeds(G) # Aggiungi velocità agli archi in km/h 'speed_kph'
    G = ox.routing.add_edge_travel_times(G) # Aggiungi tempi di percorrenza agli archi in secondi s 'travel_time'
    G = ox.distance.add_edge_lengths(G) # Aggiungi lunghezze degli archi in metri m 'length'
    # Aggiungi stazioni di ricarica casuali
    all_nodes = list(G.nodes)
    # Scegli un numero casuale di stazioni di ricarica
    charging_stations = random.sample(all_nodes, num_charging_stations)
    G = ox.utils_graph.convert.to_digraph(G, weight="travel_time") # Converte MultiDiGraph in DiGraph
    #G = G.to_undirected() # Converte in un grafo non diretto
    for node in charging_stations:
        G.nodes[node]['charging_station'] = True

    return G, charging_stations

# Funzione per disegnare il percorso sulla mappa
def draw_solution_on_map(graph, solution, start_node, end_node, charging_stations):
    # Crea una mappa centrata sulla posizione media dei nodi
    start_node_coordinates = [graph.nodes[start_node]['y'], graph.nodes[start_node]['x']]
    # Crea una mappa con folium
    m = folium.Map(location=start_node_coordinates,tiles='CartoDB Positron', zoom_start=14)
    # Disegna il percorso sulla mappa
    for action in solution:
        start_node_data = graph.nodes[action[0]]
        end_node_data = graph.nodes[action[1]]
        start_pos = [start_node_data['y'], start_node_data['x']]
        end_pos = [end_node_data['y'], end_node_data['x']]
        folium.PolyLine(locations=[start_pos, end_pos], color="red", weight=2.5, opacity=1).add_to(m)
    # Aggiungi marcatori per il nodo di partenza e di destinazione
    folium.Marker(location=[graph.nodes[start_node]['y'], graph.nodes[start_node]['x']], popup='Start', icon=folium.Icon(color='blue',prefix='fa',icon='car')).add_to(m)
    folium.Marker(location=[graph.nodes[end_node]['y'], graph.nodes[end_node]['x']], popup='End', icon=folium.Icon(color='red', prefix='fa', icon='map-pin')).add_to(m)
    # Crea un oggetto MarkerCluster
    marker_cluster = MarkerCluster().add_to(m)
    # Aggiungi marcatori per tutte le stazioni di ricarica
    for station in charging_stations:
        station_data = graph.nodes[station]
        folium.Marker(location=[station_data['y'], station_data['x']], popup=f'Charging Station: {station}', icon=folium.Icon(color='green', prefix='fa', icon='bolt')).add_to(marker_cluster)
    return m
    
# Funzione per trovare il nodo più vicino che esiste nel grafo
def nearest_existing_node(G, lat, lon):
    nodes = np.array([[data['y'], data['x']] for _, data in G.nodes(data=True)])
    tree = BallTree(nodes, leaf_size=2)
    index = tree.query([[lat, lon]], k=1, return_distance=False)[0][0]
    return list(G.nodes)[index]

# Funzione per verificare che la città inserita esista
#NONSIUSA
def get_city(geolocator, city):
    city = city.capitalize()
    try:
        result = geolocator.geocode(city)
        if result is not None:
            return result.address  # Restituisce il nome del luogo
        else:
            print("La città inserita non esiste. Per favore, riprova.")
    except GeocoderTimedOut:
        print("Errore di timeout del geolocalizzatore. Per favore, riprova.")

# Funzione per verificare che il luogo inserito esista
def get_coordinates(geolocator, location):
    location = location.capitalize()
    try:
        result = geolocator.geocode(location)
        if result is not None:
            return result  # Restituisce l'oggetto Location, non solo l'indirizzo
        else:
            print("Il luogo inserito non esiste. Per favore, riprova.")
    except GeocoderTimedOut:
        print("Errore di timeout del geolocalizzatore. Per favore, riprova.")


# Funzione principale
def main(battery_at_goal_percent, location_city, start_coordinates, end_coordinates, battery_capacity, electric_constant):
    start_time = time.time()
    # Impostazioni iniziali
    battery_capacity = battery_capacity   # Imposta la capacità massima della batteria in kWh
    electric_constant = electric_constant     # Imposta la costante elettrica
    battery = battery_capacity # Imposta la batteria iniziale
    battery_at_goal_percent = int(battery_at_goal_percent)

    battery_at_goal = battery_capacity * battery_at_goal_percent / 100 # Batteria minima in percentuale
    electric_vehicle = ev.ElectricVehicle(battery_capacity, battery, battery_at_goal, electric_constant)

    ambient_temperature = 20     # Imposta la temperatura ambientale
    num_charging_stations = 10000 # Numero di stazioni di ricarica
    
    # Crea un geolocalizzatore
    geolocator = Nominatim(user_agent = "bsGeocoder")

    # Genera il grafo e le stazioni di ricarica
    G, charging_stations = generate_osm_graph(location_city, num_charging_stations)
    
    # Trova il nodo più vicino al punto di partenza e di destinazione
    start_node = nearest_existing_node(G, start_coordinates.latitude, start_coordinates.longitude)
    end_node = nearest_existing_node(G, end_coordinates.latitude, end_coordinates.longitude)

    print(start_node, end_node)
    print("tempo inizio ricerca", time.time() - start_time)
    solution = ev.ElectricVehicle.adaptive_search(electric_vehicle, G, start_node, end_node, ambient_temperature)

    print("tempo fine ricerca", time.time() - start_time)
    if solution:
        m = draw_solution_on_map(G, solution, start_node, end_node, charging_stations)
        # Salva la mappa come HTML
        m.save("path.html")
        webbrowser.open('path.html')
    else:    
        print("Percorso non trovato")

    print("battery", electric_vehicle.battery, "energia ricaricata", electric_vehicle.energy_recharged, "tempo in ore", electric_vehicle.travel_time / 3600)
    print("Macchina ricaricata ", electric_vehicle.recharge, " volte")
    print("Soluzione:", solution)
    print("Percorso trovato con", len(solution), "azioni")
    print("Fine simulazione")


import tkinter as tk
import customtkinter as ctk
import tkinter.messagebox

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

def change_mode():
    if var.get():
        # Modalità scura
        ctk.set_appearance_mode("dark")
    else:
        # Modalità chiara
        ctk.set_appearance_mode("light")

    # Aggiorna i colori dei widget
    root.update_idletasks()

# Crea la finestra principale
root = ctk.CTk()

# Imposta le dimensioni della finestra
window_width = 800
window_height = 600

# Ottieni le dimensioni dello schermo
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Calcola la posizione per centrare la finestra
position_top = int(screen_height / 2 - window_height / 2)
position_left = int(screen_width / 2 - window_width / 2)

# Posiziona la finestra al centro dello schermo
root.geometry(f"{window_width}x{window_height}+{position_left}+{position_top}")

# Rendi la finestra non ridimensionabile
root.resizable(False, False)

# Crea un Checkbutton per cambiare la modalità
var = tk.IntVar()
checkbutton = ctk.CTkSwitch(root, text="Modalità scura", variable=var, command=change_mode)
checkbutton.pack(anchor='ne', padx=10, pady=10)

# Crea un titolo di benvenuto
welcome_label = ctk.CTkLabel(root, text = "Benvenuto nel Path Finder per veicoli elettrici!", font = ("Helvetica", 24))
welcome_label.pack(pady = 20)

# Crea una combobox per selezionare un veicolo elettrico
label_vehicle = ctk.CTkLabel(root, text = "Seleziona un veicolo elettrico:", font = ("Arial", 14))
label_vehicle.pack(pady = 2)

def combobox_callback(choice):
    print("combobox dropdown clicked:", choice)

vehicle_var = ctk.StringVar(value = list(electric_vehicle_data.keys())[0])
vehicle_combobox = ctk.CTkComboBox(root, values = list(electric_vehicle_data.keys()),
                                    command = combobox_callback, variable = vehicle_var)
vehicle_combobox.pack(pady = 1)

# Crea i widget
label_battery = ctk.CTkLabel(root, text="Inserisci la percentuale di batteria minima di arrivo:", font = ("Arial", 14))
label_battery.pack(pady = 1)
entry_battery = ctk.CTkEntry(root)
entry_battery.pack(pady = 1)

label_location = ctk.CTkLabel(root, text="Inserisci la città o il paese:", font = ("Arial", 14))
label_location.pack(pady = 1)
entry_location = ctk.CTkEntry(root)
entry_location.pack(pady = 1)

label_start = ctk.CTkLabel(root, text="Inserisci il luogo di partenza:", font = ("Arial", 14))
label_start.pack(pady = 1)
entry_start = ctk.CTkEntry(root)
entry_start.pack(pady = 1)

label_end = ctk.CTkLabel(root, text="Inserisci il luogo di destinazione:", font = ("Arial", 14))
label_end.pack(pady = 1)
entry_end = ctk.CTkEntry(root)
entry_end.pack(pady = 1)

def run_algorithm():
    # Ottieni i valori inseriti dall'utente
    battery_at_goal_percent = entry_battery.get()
    location_city = entry_location.get()
    start_location = entry_start.get()
    end_location = entry_end.get()

    # Crea un geolocalizzatore
    geolocator = Nominatim(user_agent = "bsGeocoder")

    # Ottieni le coordinate dei luoghi di partenza e di destinazione
    start_coordinates = get_coordinates(geolocator, start_location)
    end_coordinates = get_coordinates(geolocator, end_location)

    # Verifica se i valori inseriti sono validi
    if start_coordinates is None:
        tkinter.messagebox.showerror("Errore", "Il luogo di partenza inserito non esiste. Per favore, riprova.")
        entry_start.delete(0, 'end')
    if end_coordinates is None:
        tkinter.messagebox.showerror("Errore", "Il luogo di destinazione inserito non esiste. Per favore, riprova.")
        entry_end.delete(0, 'end')
    if location_city is None:
        tkinter.messagebox.showerror("Errore", "La città o il paese inserito non esiste. Per favore, riprova.")
        entry_location.delete(0, 'end')
    if battery_at_goal_percent is None:
        tkinter.messagebox.showerror("Errore", "La percentuale di batteria minima di arrivo inserita non è valida. Per favore, riprova.")
        entry_battery.delete(0, 'end')

    # Se tutti i valori sono validi, chiama la funzione main
    if start_coordinates is not None and end_coordinates is not None and location_city is not None and battery_at_goal_percent is not None:
        selected_vehicle = vehicle_combobox.get()
        vehicle_data = electric_vehicle_data[selected_vehicle]
        battery_capacity = vehicle_data["battery_capacity_kWh"]
        electric_constant = vehicle_data["electric_constant"]
        main(battery_at_goal_percent, location_city, start_coordinates, end_coordinates, battery_capacity, electric_constant)

button_run = ctk.CTkButton(root, text = "Esegui", command = run_algorithm)

# Posiziona i widget con dello spazio extra
entry_battery.pack(pady = 1)
entry_location.pack(pady = 1)
entry_start.pack(pady = 1)
entry_end.pack(pady = 1)
button_run.pack(pady = 15)

# Avvia il loop principale
root.mainloop()
