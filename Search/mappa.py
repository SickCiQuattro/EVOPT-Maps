import osmnx as ox
import networkx as nx

ox.settings.use_cache = True

G = ox.graph_from_place('Milan, Italy', network_type='drive')  # Scarica i dati della rete stradale da OSM

# Aggiungi velocità e tempi di percorrenza agli archi
G = ox.add_edge_speeds(G)  # Aggiungi velocità agli archi
G = ox.add_edge_travel_times(G)  # Aggiungi tempi di percorrenza agli archi
costo = 0.05  # Coefficiente di consumo della batteria
for u, v, k, data in G.edges(keys=True, data=True):
    speed = data['speed_kph']
    distance = data['length']
    print(f"Speed: {speed}, Distance: {distance}")
    # Calculate battery consumption based on distance, speed, and slope
    battery_consumption = costo * distance * speed / 21
    # Add battery consumption to the current node
    data['battery_consumption'] = battery_consumption
    print(f"Battery consumption: {battery_consumption}")

# Aggiungi stazioni di ricarica casuali se non sono già presenti
print('fine')