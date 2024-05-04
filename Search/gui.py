import folium
import osmnx as ox
import random
import time
import electric_vehicle as ev
import numpy as np
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# Funzione per generare un grafo da OpenStreetMap
def generate_osm_graph(location, dist, network_type, num_charging_stations):
    # Genera un grafo da OpenStreetMap
    # G = ox.graph_from_point(location, dist=dist, network_type=network_type, simplify=False)
    G = ox.graph_from_place('Brescia', network_type='drive')  # Scarica i dati della rete stradale da OSM
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
    location = np.mean([[graph.nodes[node]['y'], graph.nodes[node]['x']] for node in graph.nodes], axis=0)
    # Crea una mappa con folium
    m = folium.Map(location=location,tiles='CartoDB Positron', zoom_start=14)
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

# Funzione principale
def main():
    start_time = time.time()
    # Impostazioni iniziali

    battery_capacity = 13   # Imposta la capacità massima della batteria in kWh
    battery_at_goal_percent = 20     # Imposta la batteria minima di arrivo in %
    electric_constant = 0.7     # Imposta la costante elettrica
    battery = battery_capacity # Imposta la batteria iniziale

    battery_at_goal = battery_capacity * battery_at_goal_percent / 100 # Batteria minima in percentuale
    electric_vehicle = ev.ElectricVehicle(battery_capacity, battery, battery_at_goal, electric_constant)

    ambient_temperature = 20     # Imposta la temperatura ambientale
    location_point = (37.79, -122.41) # Esempio: San Francisco
    #location_point = (45.5257, 10.2283) # Esempio: Milano
    num_charging_stations = 6000 # Numero di stazioni di ricarica
    # Genera il grafo e le stazioni di ricarica
     # Crea un geolocalizzatore
    geolocator = Nominatim(user_agent="bsGeocoder")

    # Ottieni le coordinate geografiche della città o del paese
    start_coordinates = input("Inserisci il punto di partenza: ")
    start_coordinates_result = geolocator.geocode(start_coordinates)

    end_coordinates = input("Inserisci il nome della città o del paese: ")
    end_coordinates_result = geolocator.geocode(end_coordinates)

    G, charging_stations = generate_osm_graph(location_point, 3000, 'drive', num_charging_stations)
    # Scegli un nodo di partenza e di arrivo casuale
    #nodes_list = list(G.nodes())
    #start_node = random.choice(nodes_list)
    #end_node = random.choice(nodes_list)
    # Trova il nodo più vicino
    start_nearest_node = ox.nearest_nodes(G, start_coordinates_result.longitude, start_coordinates_result.latitude)
    end_nearest_node = ox.nearest_nodes(G, end_coordinates_result.longitude, end_coordinates_result.latitude)

    # Ottieni le coordinate del nodo
    start_node_lat, start_node_lon = G.nodes[start_nearest_node]['y'], G.nodes[start_nearest_node]['x']
    end_node_lat, end_node_lon = G.nodes[end_nearest_node]['y'], G.nodes[end_nearest_node]['x']
    
    start_node=[start_node_lat, start_node_lon]
    end_node=[end_node_lat, end_node_lon]
    print(type(start_node), type(end_node))
    print("tempo inizio ricerca", time.time()-start_time)
    solution = ev.ElectricVehicle.adaptive_search_nonricorsiva(electric_vehicle, G, start_node, end_node, ambient_temperature)

    print("tempo fine ricerca", time.time()-start_time)
    if solution:
        m = draw_solution_on_map(G, solution, start_node, end_node, charging_stations)
        # Salva la mappa come HTML
        m.save("path.html")
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
