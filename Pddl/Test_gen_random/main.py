import random
import string
from string import Template

# Assumi che il template sia nella stessa directory dello script
template_name = "/Users/filippocamossi/Documents/GitHub/ElectricRecharge/Pddl/Test_gen_random/problems.pddl"

def generate_instance(instance_name, num_stations, num_locations, battery_level, min_battery_at_goal):
    with open(template_name) as instream:
        text = instream.read()
        template = string.Template(text)
    
    # Genera i nomi delle stazioni di ricarica e delle località
    stations = ' '.join(['station{}'.format(i) for i in range(num_stations)])
    locations = ' '.join(['location{}'.format(i) for i in range(num_locations)])
    
    # Mappa per sostituire i placeholder nel template
    template_mapping = {
        'instance_name': instance_name,
        'domain_name': 'domain_electric_vehicle',
        'vehicle_name': 'vehicle0',  # Un solo veicolo
        'station_name_list': stations,
        'location_name_list': locations,
        'vehicle_position': f'(at vehicle0 location0)',
        'station_charging_rates': '\n'.join([f'(= (charging_rate station{i}) {random.randint(20, 40)})' for i in range(num_stations)]),
        'location_distances': '\n'.join([f'(= (distance location{i} location{i+1}) {random.randint(5, 30)})' for i in range(num_locations - 1)]),
        'vehicle_at_destination': f'(at vehicle0 location{num_locations - 1})',
        'vehicle_full_battery': f'(>= (battery_level vehicle0) {min_battery_at_goal})'
    }
    
    # Sostituisci i placeholder con i valori reali
    instance_content = template.substitute(template_mapping)
    
    # Salva il problema generato in un file
    with open('generated_problems.pddl', 'w') as file:
        file.write(instance_content)

    return instance_content

# Esempio di utilizzo:
instance_content = generate_instance('instance_1', 2, 3, 100, 20)
print(instance_content)