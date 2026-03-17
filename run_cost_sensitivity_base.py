
# THIS FILE RUNS THE BASE SCENARIO WITH SENSITIVITY ANALYSIS ON TECHNOLOGY COSTS

# The costs.csv file contains the cost parameters for each technology for a specific year
# This script switches costs.csv files over the horizon, every five years

# Define scenario folder and scenario name
scen_folder = 'test_runs/test_base/base_cost_sensitivity'
scen = 'test_BASE_cost_sensitivity'

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

# Scaling factors for demand in the new costs scenario
scale_demand_new_costs = {
    2025: 1.060816836,
    2026: 1.033372562,
    2027: 1.027658017,
    2028: 1.032454682,
    2029: 1.030974469,
    2030: 1.235776708, # scaling factor for 2030 in new costs scenario as it scales from 2024 to 2030
    2031: 1.029585799,
    2032: 1.029366414,
    2033: 1.048001634,
    2034: 1.041580000,
    2035: 1.489085954, # scaling factor for 2035 in new costs scenario as it scales from 2024 to 2035
    2036: 1.041580000,
    2037: 1.041580000,
    2038: 1.041580000,
    2039: 1.041580000,
    2040: 1.825504585, # scaling factor for 2040 in new costs scenario as it scales from 2024 to 2040
    'back':0.569269673, # scaling factor for scaling from 2035 to 2021
    'direct' : 1.7566367 # scaling factor from 2021 to 2035
}

# Scaling factors for sudden cost changes
scale_cost_sudden = {
    ('OCGT', 2025): 1.0,
    ('OCGT', 2026): 1.0,
    ('OCGT', 2027): 0.175,
    ('OCGT', 2028): 0.175,
    ('OCGT', 2029): 0.175,
    ('OCGT', 2030): 0.175,
    ('OCGT', 2031): 0.175,
    ('OCGT', 2032): 0.175,
    ('OCGT', 2033): 0.175,
    ('OCGT', 2034): 0.175,
    ('OCGT', 2035): 0.175,
    ('OCGT', 2036): 0.175,
    ('OCGT', 2037): 0.175,
    ('OCGT', 2038): 0.175,
    ('OCGT', 2039): 0.175,
    ('OCGT', 2040): 0.175,

    ('CCGT', 2025): 1.0,
    ('CCGT', 2026): 1.0,
    ('CCGT', 2027): 0.175,
    ('CCGT', 2028): 0.175,
    ('CCGT', 2029): 0.175,
    ('CCGT', 2030): 0.175,
    ('CCGT', 2031): 0.175,
    ('CCGT', 2032): 0.175,
    ('CCGT', 2033): 0.175,
    ('CCGT', 2034): 0.175,
    ('CCGT', 2035): 0.175,
    ('CCGT', 2036): 0.175,
    ('CCGT', 2037): 0.175,
    ('CCGT', 2038): 0.175,
    ('CCGT', 2039): 0.175,
    ('CCGT', 2040): 0.175,

    ('oil', 2025): 1.0,
    ('oil', 2026): 1.0,
    ('oil', 2027): 0.270,
    ('oil', 2028): 0.270,
    ('oil', 2029): 0.270,
    ('oil', 2030): 0.270,
    ('oil', 2031): 0.270,
    ('oil', 2032): 0.270,
    ('oil', 2033): 0.270,
    ('oil', 2034): 0.270,
    ('oil', 2035): 0.270,
    ('oil', 2036): 0.270,
    ('oil', 2037): 0.270,
    ('oil', 2038): 0.270,
    ('oil', 2039): 0.270,
    ('oil', 2040): 0.270,
}

# Scaling factors for gradual cost changes
scale_cost_gradual = {
    ('OCGT', 2025): 0.761,
    ('OCGT', 2026): 0.614,
    ('OCGT', 2027): 0.515,
    ('OCGT', 2028): 0.443,
    ('OCGT', 2029): 0.389,
    ('OCGT', 2030): 0.347,
    ('OCGT', 2031): 0.313,
    ('OCGT', 2032): 0.285,
    ('OCGT', 2033): 0.261,
    ('OCGT', 2034): 0.241,
    ('OCGT', 2035): 0.224,
    ('OCGT', 2036): 0.210,
    ('OCGT', 2037): 0.197,
    ('OCGT', 2038): 0.185,
    ('OCGT', 2039): 0.175,
    ('OCGT', 2040): 0.175,

    ('CCGT', 2025): 0.761,
    ('CCGT', 2026): 0.614,
    ('CCGT', 2027): 0.515,
    ('CCGT', 2028): 0.443,
    ('CCGT', 2029): 0.389,
    ('CCGT', 2030): 0.347,
    ('CCGT', 2031): 0.313,
    ('CCGT', 2032): 0.285,
    ('CCGT', 2033): 0.261,
    ('CCGT', 2034): 0.241,
    ('CCGT', 2035): 0.224,
    ('CCGT', 2036): 0.210,
    ('CCGT', 2037): 0.197,
    ('CCGT', 2038): 0.185,
    ('CCGT', 2039): 0.175,
    ('CCGT', 2040): 0.175,

    ('oil', 2025): 0.847,
    ('oil', 2026): 0.735,
    ('oil', 2027): 0.649,
    ('oil', 2028): 0.581,
    ('oil', 2029): 0.526,
    ('oil', 2030): 0.480,
    ('oil', 2031): 0.442,
    ('oil', 2032): 0.409,
    ('oil', 2033): 0.381,
    ('oil', 2034): 0.356,
    ('oil', 2035): 0.335,
    ('oil', 2036): 0.316,
    ('oil', 2037): 0.299,
    ('oil', 2038): 0.283,
    ('oil', 2039): 0.270,
    ('oil', 2040): 0.270,
}

# Decommissioning data
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

# Emission reduction targets
start_year = 2024
start_value = 2740892 #2784650 #2533122 #2728743
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

# Function to get cost parameters for a specific technology
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

# Function that implements yearly changes on the network
def yearly_changes(n,year):
    print(year)
    # ------- DEMAND ---------
    upscaling_factor = scale_demand_new_costs[year]
    n.loads_t.p_set = n.loads_t.p_set * upscaling_factor

    # ------- EMISSIONS -------
    # n.global_constraints.constant = emission_limit[year]
    #display(n.global_constraints.constant)

    #-------- COSTS ---------
    # indexes = {}
    # for car in ['OCGT', 'CCGT', 'oil']:
    #     mask = n.generators['carrier'] == car
    #     indexes[car] = n.generators.index[mask].tolist()
    # for car in indexes:
    #     #n.generators.loc[indexes[car], 'marginal_cost'] = n.generators.loc[indexes[car], 'marginal_cost'] / scale_cost_sudden[(car, year)]
    #     VOM, fuel, efficiency = cost_parameters(car)
    #     scaled_fuel = fuel / scale_cost_gradual[(car, year)]    
    #     n.generators.loc[indexes[car], 'marginal_cost'] = VOM + (scaled_fuel / efficiency)
        
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

# Function to implement yearly changes on the network for every fifth year
def yearly_changes_cost_year(n,year):
    print(year)
    # ------- DEMAND ---------
    upscaling_factor = scale_demand_new_costs[year]
    n.loads_t.p_set = n.loads_t.p_set * upscaling_factor

    # ------- EMISSIONS -------
    # n.global_constraints.constant = emission_limit[year]
    #display(n.global_constraints.constant)

    #-------- COSTS ---------
    # indexes = {}
    # for car in ['OCGT', 'CCGT', 'oil']:
    #     mask = n.generators['carrier'] == car
    #     indexes[car] = n.generators.index[mask].tolist()
    # for car in indexes:
    #     #n.generators.loc[indexes[car], 'marginal_cost'] = n.generators.loc[indexes[car], 'marginal_cost'] / scale_cost_sudden[(car, year)]
    #     VOM, fuel, efficiency = cost_parameters(car)
    #     scaled_fuel = fuel / scale_cost_gradual[(car, year)]    
    #     n.generators.loc[indexes[car], 'marginal_cost'] = VOM + (scaled_fuel / efficiency)
        

    # ------- GENERATOR EXTENSTION -----
    solved_network = f'{scen_folder}/{scen}_{year-1}.nc'
    m = pypsa.Network(solved_network)
    new_exp= m.generators.p_nom_opt
    # replace negative values with 0
    for index, value in new_exp.items():
        if value < 0:
            new_exp[index]=0
    # add expansion to previous network
    n.generators.p_nom = new_exp
    n.generators.p_nom_min = new_exp
    #display(n.generators.p_nom)

    # ------- STORES ----------
    new_stores = m.stores.e_nom_opt
    new_stores
    n.stores.e_nom = new_stores
    n.stores.e_nom_min = new_stores
    #display(n.stores.e_nom.sum())

    # ------- STORAGE UNITS -------
    new_storage = m.storage_units.p_nom_opt
    new_storage
    n.storage_units.p_nom = new_storage
    n.storage_units.p_nom_min = new_storage

    # ------- LINES -------
    new_lines = m.lines.s_nom_opt
    new_lines
    n.lines.s_nom = new_lines
    n.lines.s_nom_min = new_lines

    # ------- LINKS -------
    new_links = m.links.p_nom_opt
    new_links
    n.links.p_nom = new_links
    n.links.p_nom_min = new_links

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
        marginal_cost = 0.0103746318,
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
        marginal_cost = 0.0103746318,
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
        marginal_cost = 0.0103746318,
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
        marginal_cost = 0.0106120929,
        capital_cost = 270940.715282615,
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

# Function that renames the results file and moves it to the scenario folder
def delete_results_file(year):
    current_location = 'results/networks/'
    old_filename = "elec_s_all_ec_lcopt_Co2L-1H.nc"
    new_filename = f"deleted_{scen}_{year}.nc"
    new_location = f'{scen_folder}/'

    # Create the full paths for the old and new files
    old_file_path = os.path.join(current_location, old_filename)
    new_file_path = os.path.join(new_location, new_filename)

    # Rename the file
    os.rename(old_file_path, new_file_path)

    print('Results file deleted...')

# Function that deletes the network files elec.nc, elec_s.nc, elec_s_all, elec_s_all_ec.nc and elec_s_all_ec_lcopt_Co2L-1H.nc
def delete_network_files():
    files_to_delete = [
        'networks/elec.nc',
        'networks/elec_s.nc',
        'networks/elec_s_all.nc',
        'networks/elec_s_all_ec.nc',
        'networks/elec_s_all_ec_lcopt_Co2L-1H.nc'
    ]
    
    for file in files_to_delete:
        if os.path.exists(file):
            os.remove(file)
            print(f'Deleted {file}')
        else:
            print(f'{file} does not exist')
    
    
# Function that changes the costs.csv file to the new costs file for the given year
def change_costs_file(year):
    old_costs_file = f'data/costs.csv'
    new_costs_file = f'data/costs_new_{year}.csv'

    
    # Rename the old costs file to costs_old.csv
    os.rename(old_costs_file, f'data/costs_new_{year-5}.csv')
    print(f'Costs file changed to costs_new_{year-5}.csv...')

    # Rename the new costs file to costs.csv
    os.rename(new_costs_file, old_costs_file)

    print(f'Costs file changed to {year} costs...')

# Adjust lines to right capacity
def adjust_lines_capacity():

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

adjust_lines_capacity()

# Function to implement yearly changes on the network for every year, including cost changes every fifth year
for year in range(2024, 2041):
    n = read_network_file()
    if year == 2024:
        extend_hydro_old(n)
        save_network_file(n)
        subprocess.run(['snakemake', '-j', '14', 'solve_all_networks', '--unlock'])
        subprocess.run(['snakemake', '-j', '14', 'solve_all_networks'])
        rename_results_file(year)


    elif year in [2025, 2030, 2035, 2040, 2045, 2050]:
        change_costs_file(year)
        # Delete the network files to ensure the new costs are applied
        delete_network_files()
        subprocess.run(['snakemake', '-j', '14', 'solve_all_networks'])
        # Delete the results file
        delete_results_file(year)
        #adjust lines capacity
        adjust_lines_capacity()
        # Read the network file again after changing costs
        n = read_network_file()
        # Extend hydro and save the network file again
        #extend_hydro_old(n)
        #save_network_file(n)
        # Run the yearly changes and solve all networks
        # This is necessary because the costs have changed and the network needs to be solved again
        yearly_changes_cost_year(n, year)
        subprocess.run(['snakemake', '-j', '14', 'solve_all_networks'])
        rename_results_file(year)

    else:
        yearly_changes(n, year)
        subprocess.run(['snakemake', '-j', '14', 'solve_all_networks'])
        rename_results_file(year)
            



    