
# THIS FILE RUNS THE GRADUAL COST NZE SCENARIO

# Define scenario folder and name for saving results
scen_folder = 'test_runs/test_gradual_nze'
scen = 'test_GRADUAL_NZE'

# TO RUN WITH A DIFFERENT DISCOUNT RATE
# In config.py, change the value of the variable "discount_rate" to the desired rate.
# Change the resources/costs.csv file accordingly.
# Change scen_folder and scen to 'test_runs/test_base_nze/discount_rate_<value>' and 'test_BASE_NZE_<value>' and create the folder, respectively to save the results in the correct folder.

# Import necessary libraries
import pypsa
import pandas as pd
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import os
import subprocess
#import hydro_extendable as hyd
import math

# Define network and load line capacity data
network = 'networks/elec_s_all_ec_lcopt_Co2L-1H.nc'
n = pypsa.Network(network)

# Load the Excel file with line capacity data
lines_cap = pd.read_excel("custom_files/lines_capacity.xlsx")

lines_cap.set_index(["Line"], inplace=True)

power_factor = 0.9

for idx, row in lines_cap.iterrows():
    if math.isfinite(row["capacity"]):
        n.lines.at[idx, 's_nom'] = row['capacity'] * power_factor
        n.lines.at[idx, 's_nom_min'] = n.lines.at[idx, 's_nom']
        n.lines.at[idx, 's_nom_max'] = 1e5

n.export_to_netcdf('networks/elec_s_all_ec_lcopt_Co2L-1H.nc')

# Define scaling factors for demand and costs
scale_demand = {
    2025: 1.060816836,
    2026: 1.033372562,
    2027: 1.027658017,
    2028: 1.032454682,
    2029: 1.030974469,
    2030: 1.030564438,
    2031: 1.029585799,
    2032: 1.029366414,
    2033: 1.048001634,
    2034: 1.041580000,
    2035: 1.041580000,
    2036: 1.041580000,
    2037: 1.041580000,
    2038: 1.041580000,
    2039: 1.041580000,
    2040: 1.041580000,
    'back':0.569269673, # scaling factor for scaling from 2035 to 2021
    'direct' : 1.7566367 # scaling factor from 2021 to 2035
}

scale_cost_gradual = {
    ('OCGT', 2025): 0.79,
    ('OCGT', 2026): 0.65,
    ('OCGT', 2027): 0.55,
    ('OCGT', 2028): 0.48,
    ('OCGT', 2029): 0.43,
    ('OCGT', 2030): 0.38,
    ('OCGT', 2031): 0.35,
    ('OCGT', 2032): 0.32,
    ('OCGT', 2033): 0.29,
    ('OCGT', 2034): 0.27,
    ('OCGT', 2035): 0.25,
    ('OCGT', 2036): 0.24,
    ('OCGT', 2037): 0.22,
    ('OCGT', 2038): 0.21,
    ('OCGT', 2039): 0.20,
    ('OCGT', 2040): 0.20,

    ('CCGT', 2025): 0.79,
    ('CCGT', 2026): 0.65,
    ('CCGT', 2027): 0.55,
    ('CCGT', 2028): 0.48,
    ('CCGT', 2029): 0.43,
    ('CCGT', 2030): 0.38,
    ('CCGT', 2031): 0.35,
    ('CCGT', 2032): 0.32,
    ('CCGT', 2033): 0.29,
    ('CCGT', 2034): 0.27,
    ('CCGT', 2035): 0.25,
    ('CCGT', 2036): 0.24,
    ('CCGT', 2037): 0.22,
    ('CCGT', 2038): 0.21,
    ('CCGT', 2039): 0.20,
    ('CCGT', 2040): 0.20,

    ('oil', 2025): 0.86,
    ('oil', 2026): 0.75,
    ('oil', 2027): 0.67,
    ('oil', 2028): 0.60,
    ('oil', 2029): 0.55,
    ('oil', 2030): 0.50,
    ('oil', 2031): 0.46,
    ('oil', 2032): 0.43,
    ('oil', 2033): 0.40,
    ('oil', 2034): 0.37,
    ('oil', 2035): 0.35,
    ('oil', 2036): 0.33,
    ('oil', 2037): 0.32,
    ('oil', 2038): 0.30,
    ('oil', 2039): 0.29,
    ('oil', 2040): 0.29,
}

# Define decommissioning profiles
decom = {
2025 : {'C29.0' : 16.84},
2026 : {'C60.0' : 49.76, 'C61.0' : 51.37},
2027 : {'C30.0' : 15.99},
2028 : {},
2029 : {'C33.0' : 57.14, 'C34.0' : 55.97},
2030 : {'C31.0' : 18.1, 'C65.0' : 42.41, 'C66.0' : 41.15},
2031 : {},
2032 : {'C76.0' : 1.1, 'C77.0' : 1.12, 'C78.0' : 1.12},
2033 : {},
2034 : {},
2035 : {'C79.0' : 1.1, 'C80.0' : 1.1, '75 solar' : 5, '44 onwind' : 44, '42 onwind' : 39.6, '79 onwind' : 50.4},
2036 : {'22 hydro': 11.49},
2037 : {'6 hydro': 6.81, 'C35.0' : 57, 'C46.0' : 1.49, 'C47.0' : 1.49, 'C48.0' : 1.6},
2038 : {'C32.0' : 18.79, 'C49.0' : 1.55, 'C50.0' : 1.51, 'C51.0' : 1.6},
2039 : {'C98.0' : 21},
2040 : {'C68.0' : 26.43, 'C69.0' : 25.8, 'C70.0' : 26.81, 'C71.0' : 26.17, 'C75.0' : 1.28},
}

decom_storage = {
2025: {},
2026: {},
2027: {},
2028: {},
2029: {},
2030: {},
2031: {'15 hydro': 2.55},
2032: {},
2033: {},
2034: {},
2035: {},
2036: {'16 hydro' : 6.23},
2037: {},
2038: {},
2039: {'17 hydro' : 6.2},
2040: {},
}

# Define emission reduction targets
start_year = 2024
start_value = 2740892 
end_year = 2050
end_value = 0

years = range(start_year, end_year + 1)
emissions = []

decrease_per_year = (start_value - end_value) / (end_year - start_year)

for i in years:
    emission = max(start_value - decrease_per_year * (i - start_year), end_value)
    emissions.append(emission)

# Make into dict
index = np.arange(2024,2051)
emission_limit = dict(zip(index, emissions))
emission_limit

# Function to read the network file
def read_network_file():
    network = 'networks/elec_s_all_ec_lcopt_Co2L-1H.nc'
    n = pypsa.Network(network)
    return n

# Function to extract cost parameters for a given technology
def cost_parameters(tech):
    costs = pd.read_csv('data/costs.csv')
    costs_pivot = costs.pivot(index='technology', columns='parameter', values='value')
    costs_pivot['fuel'].fillna(0, inplace=True)
    costs_pivot['VOM'].fillna(0, inplace=True)
    costs_pivot['efficiency'].fillna(1, inplace=True)

    if tech == 'OCGT' or tech == 'CCGT':
        fuel = costs_pivot.at['gas', 'fuel']
    else:
        fuel = costs_pivot.at[tech, 'fuel']
   
    VOM = costs_pivot.at[tech, 'VOM']
    efficiency = costs_pivot.at[tech, 'efficiency']

    return VOM, fuel, efficiency

# Function that implements yearly changes of the network
def yearly_changes(n,year):
    print(year)
    # ------- DEMAND ---------
    upscaling_factor = scale_demand[year]
    n.loads_t.p_set = n.loads_t.p_set * upscaling_factor

    # ------- EMISSIONS -------
    n.global_constraints.constant = emission_limit[year]
    #display(n.global_constraints.constant)

    #-------- COSTS ---------
    indexes = {}
    for car in ['OCGT', 'CCGT', 'oil']:
        mask = n.generators['carrier'] == car
        indexes[car] = n.generators.index[mask].tolist()
    for car in indexes:
        #n.generators.loc[indexes[car], 'marginal_cost'] = n.generators.loc[indexes[car], 'marginal_cost'] / scale_cost_sudden[(car, year)]
        VOM, fuel, efficiency = cost_parameters(car)
        scaled_fuel = fuel / scale_cost_gradual[(car, year)]    
        n.generators.loc[indexes[car], 'marginal_cost'] = VOM + (scaled_fuel / efficiency)

    # ------- GENERATOR EXTENSTION -----
    solved_network = f'{scen_folder}/{scen}_{year-1}.nc'
    m = pypsa.Network(solved_network)
    additional_exp= m.generators.p_nom_opt - m.generators.p_nom
    # replace negative values with 0
    for index, value in additional_exp.items():
        if value < 0:
            additional_exp[index]=0
    # add expansion to previous network
    n.generators.p_nom = n.generators.p_nom.add(additional_exp, fill_value=0)
    n.generators.p_nom_min = n.generators.p_nom_min.add(additional_exp, fill_value=0)
    #display(n.generators.p_nom)

    # ------- STORES ----------
    additional_stores = m.stores.e_nom_opt - m.stores.e_nom
    additional_stores
    n.stores.e_nom = n.stores.e_nom.add(additional_stores, fill_value = 0)
    n.stores.e_nom_min = n.stores.e_nom_min.add(additional_stores, fill_value = 0)
    #display(n.stores.e_nom.sum())

    # ------- STORAGE UNITS -------
    addiional_storage = m.storage_units.p_nom_opt - m.storage_units.p_nom
    addiional_storage
    n.storage_units.p_nom = n.storage_units.p_nom.add(addiional_storage, fill_value = 0)
    n.storage_units.p_nom_min = n.storage_units.p_nom_min.add(addiional_storage, fill_value = 0)

    # ------- LINES -------
    additional_lines = m.lines.s_nom_opt - m.lines.s_nom
    additional_lines
    n.lines.s_nom = n.lines.s_nom.add(additional_lines, fill_value = 0)
    n.lines.s_nom_min = n.lines.s_nom_min.add(additional_lines, fill_value = 0)

    # ------- LINKS -------
    additional_links = m.links.p_nom_opt - m.links.p_nom
    additional_links
    n.links.p_nom = n.links.p_nom.add(additional_links, fill_value = 0)
    n.links.p_nom_min = n.links.p_nom_min.add(additional_links, fill_value = 0)

    # ------- DECOM ---------
    for index,value in decom[year].items():
        n.generators.loc[index, 'p_nom'] = n.generators.loc[index].p_nom - value
        n.generators.loc[index, 'p_nom_min'] = n.generators.loc[index].p_nom_min - value

    # ------- HYDRO-DECOM-------- # is done seperately, because the  code is different
    for index,value in decom_storage[year].items():
        n.storage_units.loc[index,'p_nom'] = n.storage_units.loc[index].p_nom - value

    # ------- SAVING ----------
    n.export_to_netcdf('networks/elec_s_all_ec_lcopt_Co2L-1H.nc')

# Function to extend the hydro generation capacity in the network
def extend_hydro_old(n):
    n.add("Generator",
        '83-6 hydro', # name of the new storage unit --> REAL NAME: UMA
        bus = '83',
        carrier = 'ror',
        p_nom = 0,
        marginal_cost = 0.01037,
        capital_cost = 185442.22646291394, #270940.715282615,
        efficiency = 0.9,
        p_nom_extendable = True,
        p_nom_max = 85
        )
 
    n.add("Generator",
        '83-7 hydro', # name of the new storage unit --> REAL NAME: PLD
        bus = '83',
        carrier = 'ror',
        p_nom = 0,
        marginal_cost = 0.01037,
        capital_cost = 185442.22646291394, #270940.715282615,
        efficiency = 0.9,
        p_nom_extendable = True,
        p_nom_max = 118
        )
   
    n.add("Generator",
        '37-1 hydro', # name of the new storage unit --> REAL NAME: JUN
        bus = '37',
        carrier = 'ror',
        p_nom = 0,
        marginal_cost = 0.01037,
        capital_cost = 185442.22646291394, #270940.715282615,
        efficiency = 0.9,
        p_nom_extendable = True,
        p_nom_max = 89.73
        )
 
    n.add("StorageUnit",
        '37-2 hydro', # name of the new storage unit --> REAL NAME: SEH
        bus = '37',
        carrier = 'hydro',
        p_nom = 0,
        marginal_cost = 0.01061,
        capital_cost = 270940.71528,
        efficiency_dispatch = 0.9,
        p_nom_extendable = True,
        p_nom_max = 194.63,
        max_hours = 6,
        p_min_pu = 0.0,
        efficiency_store = 0,
        cyclic_state_of_charge = True
        )

# Function to save the network file
def save_network_file(n):
    n.export_to_netcdf('networks/elec_s_all_ec_lcopt_Co2L-1H.nc')
    n.export_to_netcdf(f'{scen_folder}/' + scen + f'_{year}_network.nc')

# Function that renames the results file and moves it to the scenario folder
def rename_results_file(year):
    current_location = 'results/networks/'
    old_filename = "elec_s_all_ec_lcopt_Co2L-1H.nc"
    new_filename = f"{scen}_{year}.nc"
    new_location = f'{scen_folder}/'

    # Create the full paths for the old and new files
    old_file_path = os.path.join(current_location, old_filename)
    new_file_path = os.path.join(new_location, new_filename)

    # Rename the file
    os.rename(old_file_path, new_file_path)

# Loop over the years and apply changes to the network
for year in range(2024, 2041):
    n = read_network_file()
    if year == 2024:
        extend_hydro_old(n)
        save_network_file(n)
        subprocess.run(['snakemake', '-j', '14', 'solve_all_networks', '--unlock'])
        subprocess.run(['snakemake', '-j', '14', 'solve_all_networks'])
        rename_results_file(year)
    else:
        yearly_changes(n, year)
        subprocess.run(['snakemake', '-j', '14', 'solve_all_networks'])
        rename_results_file(year)


    