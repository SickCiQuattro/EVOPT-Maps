import folium
import osmnx as ox
import random
import time
import electric_vehicle as ev
import numpy as np
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
import webbrowser
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
        start_pos = [graph.nodes[action[0]]['y'], graph.nodes[action[0]]['x']]
        end_pos = [graph.nodes[action[1]]['y'], graph.nodes[action[1]]['x']]
        folium.PolyLine(locations=[start_pos, end_pos], color="red", weight=2.5, opacity=1).add_to(m)
    # Aggiungi marcatori per il nodo di partenza e di destinazione
    folium.Marker(location=[graph.nodes[start_node]['y'], graph.nodes[start_node]['x']], popup='Start', icon=folium.Icon(color='blue',prefix='fa',icon='car')).add_to(m)
    folium.Marker(location=[graph.nodes[end_node]['y'], graph.nodes[end_node]['x']], popup='End', icon=folium.Icon(color='red', prefix='fa', icon='map-pin')).add_to(m)
    # Crea un oggetto MarkerCluster
    marker_cluster = MarkerCluster().add_to(m)
    # Aggiungi marcatori per tutte le stazioni di ricarica
    for station in charging_stations:
        folium.Marker(location=[graph.nodes[station]['y'], graph.nodes[station]['x']], popup=f'Charging Station: {station}', icon=folium.Icon(color='green', prefix='fa', icon='bolt')).add_to(marker_cluster)
    return m
    
# Funzione per trovare il nodo più vicino che esiste nel grafo
def nearest_existing_node(G, lat, lon):
    nodes = np.array([[data['y'], data['x']] for _, data in G.nodes(data=True)])
    tree = BallTree(nodes, leaf_size=2)
    index = tree.query([[lat, lon]], k=1, return_distance=False)[0][0]
    return list(G.nodes)[index]

# Funzione per verificare che la città inserita esista
def get_city(geolocator, prompt):
    while True:
        city = input(prompt).capitalize()
        try:
            result = geolocator.geocode(city)
            if result is not None:
                return result.address  # Restituisce il nome del luogo
            else:
                print("La città inserita non esiste. Per favore, riprova.")
        except GeocoderTimedOut:
            print("Errore di timeout del geolocalizzatore. Per favore, riprova.")

# Funzione per verificare che il luogo inserito esista
def get_coordinates(geolocator, prompt):
    while True:
        location = input(prompt).capitalize()
        try:
            result = geolocator.geocode(location)
            if result is not None:
                return result
            else:
                print("Il luogo inserito non esiste. Per favore, riprova.")
        except GeocoderTimedOut:
            print("Errore di timeout del geolocalizzatore. Per favore, riprova.")

# Funzione principale
def main(battery_at_goal_percent, location_city, start_coordinates, end_coordinates):
    start_time = time.time()
    # Impostazioni iniziali
    battery_capacity = 9   # Imposta la capacità massima della batteria in kWh
    #battery_at_goal_percent = 30     # Imposta la batteria minima di arrivo in %
    # electric_constant = 0.05     # Imposta la costante elettrica
    electric_constant = 0.4     # Imposta la costante elettrica
    battery = battery_capacity # Imposta la batteria iniziale
    battery_at_goal_percent = input("Inserisci la percentuale di batteria minima di arrivo: ") # Batteria minima in percentuale
    battery_at_goal_percent = int(battery_at_goal_percent)

    battery_at_goal = battery_capacity * battery_at_goal_percent / 100 # Batteria minima in percentuale
    electric_vehicle = ev.ElectricVehicle(battery_capacity, battery, battery_at_goal, electric_constant)

    ambient_temperature = 20     # Imposta la temperatura ambientale
    num_charging_stations = 10000 # Numero di stazioni di ricarica
    
    # Crea un geolocalizzatore
    geolocator = Nominatim(user_agent="bsGeocoder")

    # Inserisci la città o il paese
    location = get_city(geolocator, "Inserisci la città o il paese: ")
    location_city = ' '+ location +' '

    # Ottieni le coordinate geografiche della città o del paese
    start_coordinates_result = get_coordinates(geolocator, "Inserisci il luogo di partenza: ")
    end_coordinates_result = get_coordinates(geolocator, "Inserisci il luogo di destinazione: ")
    # Genera il grafo e le stazioni di ricarica
    G, charging_stations = generate_osm_graph(location_city, num_charging_stations)
    
    # Trova il nodo più vicino al punto di partenza e di destinazione
    start_node = nearest_existing_node(G, start_coordinates_result.latitude, start_coordinates_result.longitude)
    end_node = nearest_existing_node(G, end_coordinates_result.latitude, end_coordinates_result.longitude)

    print(start_node, end_node)
    print("tempo inizio ricerca", time.time()-start_time)
    solution = ev.ElectricVehicle.adaptive_search(electric_vehicle, G, start_node, end_node, ambient_temperature)

    print("tempo fine ricerca", time.time()-start_time)
    if solution:
        m = draw_solution_on_map(G, solution, start_node, end_node, charging_stations)
        # Salva la mappa come HTML
        m.save("path.html")
        webbrowser.open('path.html')
    else:    
        print("Percorso non trovato")

    print("battery", electric_vehicle.battery, "energia ricaricata", electric_vehicle.energy_recharged, "tempo in ore", electric_vehicle.travel_time/3600)
    print("Macchina ricaricata ", electric_vehicle.recharge, " volte")
    print("Soluzione:", solution)
    print("Percorso trovato con", len(solution), "azioni")
    print("Fine simulazione")

# Esegui la funzione main
if __name__ == "__main__":
    main()
