import pygame
from path_finding import PathFinding
from ASTAR import AStar as ASTARPathFinder
from ElectricVehicle import ElectricVehicleAStar as ev
import heuristics

WIDTH = 1000
WIN = pygame.display.set_mode((WIDTH, WIDTH))
pygame.display.set_caption("Search Algorithm")
pygame.init()

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 255, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
GREY = (128, 128, 128)
TURQUOISE = (64, 224, 208)
CHARGING_STATION_COLOR = (0, 0, 255)  # Blu

class Spot:
    def __init__(self, row, col, width):
        self.row = row
        self.col = col
        self.x = row * width
        self.y = col * width
        self.color = WHITE
        self.width = width

    def is_charging_station(self):
        return self.color == CHARGING_STATION_COLOR
    
    def make_charging_station(self):
        self.color = CHARGING_STATION_COLOR

    def get_pos(self):
        return self.row, self.col

    def is_closed(self):
        return self.color == RED

    def is_open(self):
        return self.color == GREEN

    def is_barrier(self):
        return self.color == BLACK

    def is_start(self):
        return self.color == ORANGE

    def is_end(self):
        return self.color == TURQUOISE

    def reset(self):
        self.color = WHITE

    def make_start(self):
        self.color = ORANGE

    def make_closed(self):
        self.color = RED

    def make_open(self):
        self.color = GREEN

    def make_barrier(self):
        self.color = BLACK

    def make_end(self):
        self.color = TURQUOISE

    def make_path(self):
        self.color = PURPLE

    def draw(self, win):
        pygame.draw.rect(win, self.color, (self.x, self.y, self.width, self.width))

    def __str__(self):
        return "({},{})".format(self.row, self.col)

def make_grid(rows, width):
    grid = []
    gap = width // rows
    for i in range(rows):
        grid.append([])
        for j in range(rows):
            spot = Spot(i, j, gap)
            grid[i].append(spot)

    return grid

def make_grid_from_file(filename, width):
    f = open(filename)

    data = json.load(f)

    rows = data['rows']
    grid = []
    gap = width // rows
    
    start = (data['start'][0],data['start'][1])
    end = (data['end'][0],data['end'][1])
    
    barrier = {(ele[0],ele[1]) for ele in data['barrier']}
    
    for i in range(rows):
        grid.append([])
        for j in range(rows):
            spot = Spot(i, j, gap)
            if (i,j) in barrier:
                spot.make_barrier()
            elif (i,j) == start:
                spot.make_start()
                start = spot
            elif (i,j) == end:
                spot.make_end()
                end = spot
            grid[i].append(spot)

    return grid, start, end, rows, barrier


def draw_grid(win, rows, width):
    gap = width // rows
    for i in range(rows):
        pygame.draw.line(win, GREY, (0, i * gap), (width, i * gap))
        for j in range(rows):
            pygame.draw.line(win, GREY, (j * gap, 0), (j * gap, width))

def draw(win, grid, rows, width):
    win.fill(WHITE)

    for row in grid:
        for spot in row:
            spot.draw(win)

    draw_grid(win, rows, width)
    
    save_map_button.show()

    pygame.display.update()

def get_clicked_pos(pos, rows, width):
    gap = width // rows
    y, x = pos

    row = y // gap
    col = x // gap

    return row, col

def mark_spots(start, grid, plan):   
    x = start.row
    y = start.col
    for a in plan:
        if a == 'N':
            y+=1
        elif a == 'S':
            y-=1
        elif a == 'E':
            x+=1
        elif a == 'W':
            x-=1
        grid[x][y].make_path()         

def mark_expanded(exp, grid):
    for e in exp:
        grid[e[0]][e[1]].make_closed()

import json
def save_to_file(grid, start, end, charging_stations, filename="temp.json"):
    # Creare una lista per le barriere
    barrier = [(spot.row, spot.col) for row in grid for spot in row if spot.is_barrier()]
    # Creare una lista per le stazioni di ricarica
    charging_stations_list = [(spot.row, spot.col) for row in grid for spot in row if spot.is_charging_station()]
    
    # Creare un dizionario per i dati da salvare
    data = {
        "rows": len(grid),
        "start": (start.row, start.col),
        "end": (end.row, end.col),
        "barrier": barrier,
        "charging_stations": charging_stations_list
    }
    
    # Convertire il dizionario in una stringa JSON formattata
    json_data = json.dumps(data, indent=4)
    
    # Scrivere la stringa JSON nel file
    with open(filename, "w") as file:
        file.write(json_data)

    print(f"Map saved to {filename}")


class Button:
    """Create a button, then blit the surface in the while loop"""
 
    def __init__(self, text,  pos, font, bg="black", feedback=""):
        self.x, self.y = pos
        self.font = pygame.font.SysFont("Arial", font)
        if feedback == "":
            self.feedback = text
        else:
            self.feedback = feedback
        self.change_text(text, bg)
 
    def change_text(self, text, bg="black"):
        self.text = self.font.render(text, 1, pygame.Color("White"))
        self.size = self.text.get_size()
        self.surface = pygame.Surface(self.size)
        self.surface.fill(bg)
        self.surface.blit(self.text, (0, 0))
        self.rect = pygame.Rect(self.x, self.y, self.size[0], self.size[1])
 
    def show(self):
        WIN.blit(self.surface, (self.x, self.y))
 
    def click(self, event, grid, start, end):
        x, y = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if pygame.mouse.get_pressed()[0]:
                if self.rect.collidepoint(x, y):
                    if grid is not None and start is not None and end is not None:
                        save_to_file(grid, start, end, "tempmap.json")
                        self.change_text(self.feedback, bg="red")
                        pygame.time.delay(200)  # Aggiungi un piccolo ritardo

save_map_button = Button(
    "Save Map",
    (WIDTH-200, 100),
    font=20,
    bg="navy",
    feedback="Saved")

load_map_button = Button(
    "Load Map",
    (WIDTH-200, 200),
    font=20,
    bg="navy",
    feedback="Loaded")

clock = pygame.time.Clock()
import click
import time
@click.command()
@click.option('-w', '--width', default = WIDTH-200, help = "Width of the Windows")
@click.option('-r', '--rows', default = 50, help = "Number of rows/columns in the map")
@click.option('-s', '--search_algorithm', default = "ev", help = "Search algorithm to be used")
@click.option('-f', '--filename', default = None, help = "Initialize map with data from file")

def main(width, rows, search_algorithm, filename = None):
    win = WIN
    start = None
    end = None
    ROWS = rows
    charging_stations = set()  # Inizializza un insieme per le stazioni di ricarica

    if search_algorithm == 'ASTAR':
        search_algorithm = ASTARPathFinder(heuristics.manhattan,True)
    elif search_algorithm == 'ev':
        search_algorithm = ev(heuristics.manhattan,True)
    
    if filename is not None:
        grid, start, end, rows, wall = make_grid_from_file(filename,width) 
    else:
        grid = make_grid(rows, width)
        wall = set()
    run = True
    
    while run:
        draw(win, grid, rows, width)
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    pos = pygame.mouse.get_pos()
                    row, col = get_clicked_pos(pos, rows, width)
                    spot = grid[row][col]
                    if not spot.is_start() and not spot.is_end():
                        if spot.is_charging_station():
                            spot.reset()  # Rimuove la stazione di ricarica
                            charging_stations.remove((row, col))  # Rimuove dalla lista
                        else:
                            spot.make_charging_station()  # Aggiunge una stazione di ricarica
                            charging_stations.add((row, col))  # Aggiunge alla lista
            pygame.display.update()
            if event.type == pygame.QUIT:
                run = False
            save_map_button.click(event, grid, start, end)

            if pygame.mouse.get_pressed()[0]:  # LEFT
                pos = pygame.mouse.get_pos()
                if pos[0] < width and pos[1] < width:
                    row, col = get_clicked_pos(pos, rows, width)
                    spot = grid[row][col]
                    if not start and spot != end:
                        start = spot
                        start.make_start()
                        
                    elif not end and spot != start:
                        end = spot
                        end.make_end()

                    elif spot != end and spot != start:
                        spot.make_barrier()
                        wall.add((row,col))

            elif pygame.mouse.get_pressed()[2]: # RIGHT
                pos = pygame.mouse.get_pos()
                if pos[0] < width and pos[1] < width:
                    row, col = get_clicked_pos(pos, rows, width)
                    spot = grid[row][col]
                    spot.reset()
                    if (row, col) in wall:
                        wall.remove((row,col))
                    if spot == start:
                        start = None
                    elif spot == end:
                        end = None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and start and end:
                    world = PathFinding.World(rows - 1, rows - 1, wall)
                    problem = PathFinding(world, (start.row, start.col), (end.row, end.col), charging_stations)
                    now = time.time()
                    plan = search_algorithm.solve(problem)
                    now = time.time() - now
                    print("Number of Expansion: {} in {} seconds".format(search_algorithm.expanded, now))
                    mark_expanded(search_algorithm.expanded_states, grid)
                    if plan is not None:
                        print(plan)
                        print("Cost of the plan is: {}".format(len(plan)))
                        mark_spots(start,grid,plan)
                    draw(win, grid, rows, width)
                if event.key == pygame.K_c:
                    start = None
                    end = None
                    grid = make_grid(rows, width)
                    wall = set()

    pygame.quit()

if __name__ == '__main__':
    main()