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