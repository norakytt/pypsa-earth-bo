
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

See folder overview in README text.

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

Before each scenario run, the `networks/` folder should be cleared. Then run:

```bash
snakemake -j1 solve_all_networks
```

The run scripts to generate results need a complete network file `networks/elec_s_all_ec_lcopt_Co2L-1H.nc` (all nodes scenarios) or `networks/elec_s_4_ec_lcopt_Co2L-1H.nc` (4 nodes scenario) to run.

## 7) Main Scenario Runs

```bash
python run_scrips/run_base.py
python run_scrips/run_base_nze.py
python run_scrips/run_sudden.py
python run_scrips/run_sudden_nze.py
python run_scrips/run_gradual.py
python run_scrips/run_gradual_nze.py
```

## 8) Sensitivity Runs

Weather, tech cost, discount rate, gas price, and 4‑node model.

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
