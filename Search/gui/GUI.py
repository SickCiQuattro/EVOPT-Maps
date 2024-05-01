import csv

# Leggi i record dal file CSV
filename = 'EV_charging_station_BS.csv'
keys = ('station address', 'geographic coordinates')
records = []

# Leggi i record dal file CSV
with open(filename, 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        records.append({key: row[key] for key in keys})

# Aggiungi le coordinate di latitudine e longitudine ai record
for record in records:
    latitude, longitude = record['geographic coordinates'].split("(")[-1].split(")")[0].split()
    record['longitude'] = float(longitude)
    record['latitude'] = float(latitude)

# Creazione della mappa interattiva
import folium
import webbrowser
import http.server
import socketserver
import threading
import clipboard
import networkx as nx
from folium.plugins import MarkerCluster
from tkinter import *
import customtkinter as ctk
from tkinter.constants import CENTER
from tkinter import messagebox
from PIL import Image, ImageTk

# Definisci i luoghi di interesse
luoghi = {
    "Università di Brescia": [45.5645, 10.2302],
    "Stazione di Brescia": [45.5325558, 10.215],
    "Capriano del colle": [45.4585357, 10.1230353],
    "Darfo Boario Terme": [45.8834863, 10.1807068],
    "Lumezzane": [45.6490, 10.2632],
    "Piazza della Vittoria": [45.5384173, 10.2193704],
    "Manerbio": [45.355777, 10.13517],
    "Salò": [45.6056775, 10.520069],
    "Desenzano del Garda": [45.4701745, 10.5422455],
    "Gefran": [45.6209214, 10.0320506],
    "Iseo": [45.6598202, 10.048788], 
    "San Polino": [45.5167388, 10.2659676],
    "Poliambulanza" : [45.5173032, 10.2367065],
    "Sirmione": [45.4688494, 10.6078237],
    "Castello di Brescia": [45.5426878, 10.2250457],
    "Poncarale": [45.4606628, 10.1739092],
    "Ghedi": [45.4015124,10.2768169],
    "Orzinuovi ": [45.4020363, 9.9243428],
    "Elnòs": [45.5339261, 10.1646405],
    "Il Leone": [45.4316149, 10.5140129],
    "Ponte di legno": [46.258603, 10.508662],
    "Piazzale Arnaldo": [45.5362969, 10.2293289], 
    
}

# Create a graph
G = nx.Graph()

def submit():
    partenza = entry1.get()
    destinazione = entry2.get()

    if partenza in luoghi:
        luogo_centrale = luoghi[partenza]
        map = folium.Map(location=luogo_centrale,tiles='CartoDB Positron', zoom_start=15)
        folium.Marker(luoghi[partenza], popup='Luogo di partenza', icon=folium.Icon(color='blue', prefix='fa', icon='house')).add_to(map)
        G.add_node(partenza)
    else:
        messagebox.showerror("Errore", "Mi spiace pasticcino, luogo di partenza non trovato.")

    if destinazione in luoghi:
        folium.Marker(luoghi[destinazione], popup='Luogo di destinazione', icon=folium.Icon(color='red', prefix='fa', icon='map-pin')).add_to(map)
        G.add_node(destinazione)
    else:
        messagebox.showerror("Errore", "Mi spiace pasticcino, luogo di destinazione non trovato.")


    # Crea un oggetto MarkerCluster
    marker_cluster = MarkerCluster().add_to(map)

    for record in records:
        coords = [record['latitude'], record['longitude']]
        # Aggiungi i marker al cluster invece che direttamente alla mappa
        folium.Marker(coords, popup=record['station address'], tooltip='<strong>Click here to see Popup</strong>', icon=folium.Icon(color='green',icon='glyphicon glyphicon-flash')).add_to(marker_cluster)
        
        # Aggiungi la stazione come nodo al grafo
        G.add_node(record['station address'], pos=coords)

    # Aggiungi i bordi al grafo
    for record in records:
        G.add_edge(partenza, record['station address'])
        G.add_edge(destinazione, record['station address'])

    #DOVE AGGIUNGERE IL CALCOLO DEL PERCORSO (COPILOT )
    # Calcola il percorso più breve con l'algoritmo A*
    #percorso = nx.astar_path(G, partenza, destinazione)

    # Visualizza il percorso sul grafico
    #for i in range(len(percorso) - 1):
        #folium.PolyLine(locations=[luoghi[percorso[i]], luoghi[percorso[i+1]]], color='blue').add_to(map)


    map.save('map.html')

    # Crea un server web locale per visualizzare la mappa
    PORT = 8001
    Handler = http.server.SimpleHTTPRequestHandler

    httpd = socketserver.TCPServer(("", PORT), Handler)

    def serve_on_new_thread():
        httpd.serve_forever()

    # Avvia il server web su un nuovo thread
    threading.Thread(target=serve_on_new_thread).start()

    # Apri una nuova scheda del browser per visualizzare la mappa
    webbrowser.open_new_tab('http://localhost:8001/map.html')

ctk.set_appearance_mode("light")
root = ctk.CTk()
root.eval('tk::PlaceWindow %s center' % root.winfo_pathname(root.winfo_id()))
root.title("Mappa delle stazioni di ricarica")
root.geometry("669x356")

# Impedisce il ridimensionamento della finestra
root.resizable(False, False)

# Disabilita il pulsante di massimizzazione
root.attributes('-fullscreen', False)


# Carica e ridimensiona l'immagine di sfondo
background_image = Image.open("sfondo.jpg")  # Aggiorna con il percorso corretto dell'immagine
background_image = background_image.resize((1769, 885)) 
background_photo = ImageTk.PhotoImage(background_image)

background_label = ctk.CTkLabel(root, image=background_photo, width=669, height=376, text="")
background_label.place(x=0, y=0, relwidth=1, relheight=1)

label1 = ctk.CTkLabel(master=root, text="Inserisci il luogo di partenza:", font=("Arial", 14), fg_color=("white"))
label1.place(x=445, y=80)

entry1 = ctk.CTkEntry(root)
entry1.place(x=460, y=130, anchor='w')

label2 = ctk.CTkLabel(master=root, text="Inserisci il luogo di destinazione:", font=("Arial", 14), fg_color=("white"))
label2.place(x=445, y=150)

entry2 = ctk.CTkEntry(root)
entry2.place(x=460, y=200, anchor='w')

submit_button = ctk.CTkButton(root, text="view map", command=submit)
submit_button.place(x=460, y=230)
root.mainloop()
