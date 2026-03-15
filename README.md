
# Modeling the Bolivian Energy System with PyPSA‑Earth

Reproducibility package for **Breaking the Natural Gas Subsidy Trap:
Implications for Bolivia’s Power System Transition to 2040**, submitted to *Energy Economics* (2026).

This repository contains the code, configuration, scenarios, sensitivity scenarios, and analysis scripts to reproduce the results in the paper. The workflow is based on PyPSA-Earth with custom modifications tailored to the modeling setup in the study.

## 1) Overview

Bolivia’s electricity system is currently dominated by subsidized natural gas generation. These subsidies—priced ~80% below international levels—create large fiscal costs and distort investment incentives, while the country simultaneously faces declining domestic gas reserves and increasing uncertainty in future supply.

This repository implements all six long‑term transition scenarios evaluated in the paper to 2040. Scenarios explore:

- **How natural gas and oil subsidies shape investment decisions**
- **The impact of alternative subsidy‑reduction pathways**
  - **Base (no subsidy reform)**
  - **Sudden Cut (SC)**
  - **Gradual Cut (GC)**
- **Interactions with climate mitigation policies**
  - Net‑Zero Emissions (NZE) pathway consistent with IPCC
- **System costs, emissions, generation mix, and capacity expansion**

The study finds that Bolivia can save **up to €2.5 billion** by 2040 by reforming subsidies, while simultaneously enabling higher renewable penetration and reducing CO₂ emissions.  

This repository provides the complete modeling framework used to generate these results, including:

- PyPSA‑Earth‑BO (Bolivia‑optimized model)
- Updated Bolivian grid topology (101‑node network)
- Demand projections from CNDC
- Updated fuel prices and inflows
- Scenario scripts (Base, SC, GC + NZE variants)
- Sensitivity analyses (weather, discount rate, technology cost, gas price)
- Analysis notebooks reproducing all figures in the paper

## 2) Installation and Requirements

### 2.1 PyPSA-Earth Installation

Follow the official PyPSA-Earth installation instructions:
<https://pypsa-earth.readthedocs.io/en/latest/installation.html>

### 2.2 Our Modified PyPSA-Earth Version

This project uses a **custom fork of PyPSA-Earth v.0.3.0**, which is extended to:

- support higher spatial resolution (101 nodes)
- incorporate Bolivian grid voltage levels (69/115/230 kV)
- add realistic annual capacity addition limits
- enable extendable hydropower and geothermal capacity
- update fuel prices to reflect Bolivia’s subsidized domestic market
- correct load distribution using CNDC 2022 data
- integrate revised hydro inflows and reservoir storage

Paper source for model extensions: Kyte et al. 2026.

Repository link to PyPSA-Earth (v.0.3.0): Link to this same version?

## 3) Repository Structure

This repository follows a modular structure consistent with PyPSA‑Earth.  
Below is a description of the main folders and their purpose:

- **config/**  
  Contains all scenario configuration files (Base, Sudden, Gradual + NZE variants).  
  Each config overrides PyPSA‑Earth defaults for fuel prices, emission caps, and Bolivian system parameters.

- **custom_files/**  
  Bolivia‑specific input data that replaces or extends PyPSA‑Earth defaults.  
  Includes updated power plant lists (CNDC), fuel prices, corrected demand distribution, hydro inflows, and technology cost assumptions.

- **network/**  
  Pre‑processed 101‑node Bolivian network used as input for all scenario runs.

- **run_scripts/**  
  Python scripts that trigger each scenario (Base, Sudden, Gradual) and the NZE versions.  
  These scripts load the correct config file and set scenario‑specific switches. Also contains scripts for sensitivity analyses (weather years, discount rate, gas price, technology cost, 4‑node comparison).

- **test_runs/**  
  Configured folder to place results from the runs_scripts.

- **analysis/**  
  Jupyter notebooks and helper scripts used to reproduce all figures and tables in the paper.  
  The main notebooks are `analysis.ipynb` where .csv-files are created for the scenarios and `plots.ipynb` where all the plots from the paper can be created with the .csv-files created in `analysis.ipynb`.

- **environment.yaml**  
  Environment specification for reproducibility.

- **results/**
  Stores model outputs when scenarios are executed.

## 4) Configuration Setup

The main configuration files define:

### **Technology assumptions updated in resources/costs.csv**

Updated CAPEX/OPEX using Bolivian‑specific sources and international references:  

- Updated low subsidized gas price (4.3 €/MWh)  
- Updated diesel price (14.27 €/MWh)  
- Biomass cost reduced to 1 €/MWh  

### **Demand forecasting improved in resources/demand_profiles.csv**

- Default PyPSA‑Earth demand projections are replaced with regulator data (CNDC 2022).
- Demand grows annually according to historical + declared future consumption.

### **Hydropower inflows changed in resources/renewable_profiles/profile_hydro.nc**

- Reconstructed hourly inflows using seasonal CNDC patterns.
- Reservoir storage updated from unrealistic 6h → 1352h.

### **Emission caps (NZE) in run scripts**

- CO₂ limits consistent with IPCC NZE‑2050.

### **New model constraints in scripts/solve_all_networks.py**

- Maximum **400 MW/year** total new capacity
- Maximum **100 MW/year** geothermal expansion
- Upper bounds for biomass and geothermal potentials
- Yearly capacity factor constraint for biomass

### **Created custom powerplant, substation and lines files due to discreptancies in OSM data**

Files added to the folder `custom_files/` as backup and replaces the files with downloaded data from Open Street Map (OSM).

## 5) Custom Files

The folder `custom_files/` includes custom files which override PyPSA‑Earth defaults and includes:

| File | Description |
| ------ | ------------- |
| `custom_powerplants.csv` | Updated 2022 Bolivian power plant list (CNDC), placed in the `data/` folder |
| `costs.csv` | Adjusted Bolivian technology CAPEX/OPEX, replacing original costs-file in the `resources/` folder |
| `profile_hydro.nc/` | Reconstructed inflow profiles, replacing original profile-file in the `resources/renewable_profiles/` folder |
| `demand_profiles.csv` | Adjusted nodal load distribution, replacing original profile-file in the `resources/` folder |
| `custom_substations1.geojson` | Custom geojson with improved substations data, path added to `path_custom_substations` in the `config.yaml` file |
| `custom_lines1.geojson` | Custom geojson with improved line data, path added to `path_custom_lines` in the `config.yaml` file |

## 6) Prepare Before Scenario Runs

Build initial network by following the PyPSA-Earth documentation.

By cloning this repository, all data is available - but you need to replace the files as described in custom files.

Changes in the config.yaml-file and the model should remain as in this repository.

Before each scenario run, the `networks/` folder should be cleared. Then run:

```bash
snakemake -j1 solve_all_networks
```

The to generate results the run scripts need a complete network file `networks/elec_s_all_ec_lcopt_Co2L-1H.nc` (all nodes scenarios) or `networks/elec_s_4_ec_lcopt_Co2L-1H.nc` (4 nodes scenario) to run.

## 7) Main Scenario Runs

After the a successful installation and configuration of PyPSA-Earth-BO, you are ready to run the different scenarios. These are ready to run, and the results will appear after the run in their respective results folders as described in the run scripts.

| Scenario | Run Script |
| ------ | ------------- |
| Base | `run_scrips/run_base.py` |
| Base NZE | `run_scrips/run_base_nze.py` |
| Sudden Cost | `run_scrips/run_sudden.py` |
| Sudden Cost NZE | `run_scrips/run_sudden_nze.py` |
| Gradual Cost | `run_scrips/run_gradual.py` |
| Gradual Cost NZE | `run_scrips/run_gradual_nze.py` |

## 8) Sensitivity Runs

| Sensitivity Analysis | Scenario | Run Script |
| ------ | ------ | ------------- |
| Weather | Base 2011 | `run_scrips/run_base.py`, change weather configuration as described in run script |
| | Base 2018 | `run_scrips/run_base.py`, change weather configuration as described in run script |
| | Sudden 2011 | `run_scrips/run_sudden.py`, change weather configuration as described in run script |
| | Sudden 2018 | `run_scrips/run_sudden.py`, change weather configuration as described in run script |
| | | |
| Technology cost | Base Cost Sensitivity | `run_scrips/run_cost_sensitivity_base.py` |
| | Sudden Cost Sensitivity | `run_scrips/run_cost_sensitivity_sudden.py` |
| | Gradual Cost Sensitivity | `run_scrips/run_cost_sensitivity_gradual.py` |
| | | |
| Discount rate | Base 7% | `run_scrips/run_base.py`, change discount rate configuration as described in run script |
| | Base 10% | `run_scrips/run_base.py`, change discount rate configuration as described in run script |
| | Sudden 7% | `run_scrips/run_sudden.py`, change discount rate configuration as described in run script |
| | Sudden 10% | `run_scrips/run_sudden.py`, change discount rate configuration as described in run script |
| | Gradual 7% | `run_scrips/run_gradual.py`, change discount rate configuration as described in run script |
| | Gradual 10% | `run_scrips/run_gradual.py`, change discount rate configuration as described in run script |
| | | |
| Gas Price | Base low gas prices | N/A, static gas price. Subsidy calculations from original scenario run |
| | Base high gas prices | N/A, static gas price. Subsidy calculations from original scenario run |
| | Sudden low gas prices | `run_scrips/run_sudden_gas_price_low.py` |
| | Sudden high gas prices | `run_scrips/run_sudden_gas_price_high.py` |
| | | |
| Nodes | Gradual NZE 4 nodes | `run_scrips/run_gradual_nze_4_nodes.py` |

## 9) Analysis Scripts

```bash
analysis.ipynb
```

## 10) Citation

Add citation once paper is published.

## 11) Authors & Contact

Add author information.

## 12) License & Data Availability

Add license and data access information.
