
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

This repository provides the complete modeling framework used to generate these results, including:

- PyPSA‑Earth‑BO (Bolivia‑optimized model)
- Updated Bolivian grid topology (101‑node network)
- Demand projections from CNDC
- Updated fuel prices and inflows
- Scenario scripts (Base, SC, GC + NZE variants)
- Sensitivity analyses (weather, discount rate, technology cost, gas price)
- Analysis notebooks reproducing all figures in the paper

## 2) Installation and Requirements

### 2.1 PyPSA-Earth-BO Information

This project uses a **custom fork of PyPSA-Earth v.0.3.0**, which is extended to:

- support higher spatial resolution (101 nodes)
- incorporate Bolivian grid voltage levels (69/115/230 kV)
- add realistic annual capacity addition limits
- enable extendable hydropower and geothermal capacity
- update fuel prices to reflect Bolivia’s subsidized domestic market
- correct load distribution using CNDC 2022 data
- integrate revised hydro inflows and reservoir storage

Paper source for model extensions: Kyte et al. 2026.

More information about PyPSA-Earth can be found here:

- [PyPSA-Earth documentation](https://pypsa-earth.readthedocs.io/en/latest/)

- [PyPSA-Earth repository](https://github.com/pypsa-meets-earth/pypsa-earth/tree/main)

### 2.2 PyPSA-Earth-BO Installation

The installation and requirements are equal to those of pypsa-earth:

1. Open the terminal and go to a folder where you want to install pypsa-earth-BO. To download the package from github type the following:

    ```bash
    .../some/path/without/spaces % git clone https://github.com/norakytt/pypsa-earth-bo.git
    ```

2. Change cloned folder name from `pypsa-earth-bo` to `pypsa-earth`.

3. The python package requirements are found in environment.yaml. The environment can be installed like this:

    ```bash
    .../pypsa-earth % conda env create -f envs/environment.yaml
    ```

4. In step 2, three solvers are installed: HiGHs, glpk and gurobi. For this paper we have used gurobi.

5. To use jupyter lab (new jupyter notebooks) **continue** with the [ipython kernel installation](http://echrislynch.com/2019/02/01/adding-an-environment-to-jupyter-notebooks/) and test if your jupyter lab works:

   ```bash
   .../pypsa-earth % ipython kernel install --user --name=pypsa-earth
   .../pypsa-earth % jupyter lab

6. Verify or install a java redistribution from the [official website](https://www.oracle.com/java/technologies/downloads/) or equivalent. To verify the successful installation the following code can be tested from bash:

   ```bash
   .../pypsa-earth % java -version
   ```

   The expected output should resemble the following:

   ```bash
   java version "1.8.0_341"
   Java(TM) SE Runtime Environment (build 1.8.0_341-b10)
   Java HotSpot(TM) 64-Bit Server VM (build 25.341-b10, mixed mode)
   ```

### 2.3 Tested Environment

The workflows were tested on Python 3.10.13 with PyPSA‑Earth v.0.3.0 and Snakemake 7.32.4.

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

- **analysis_scripts/**  
  Jupyter notebooks and helper scripts used to reproduce all figures and tables in the paper.  
  The main notebooks are `analysis.ipynb` where .csv-files are created for the scenarios and plots notebooks where all the plots from the paper can be created with the .csv-files created in `analysis.ipynb`.

- **environment.yaml**  
  Environment specification for reproducibility.

- **results/**
  Stores model outputs when scenarios are executed.

## 4) Configuration & Custom Files

PyPSA‑Earth‑BO relies on a set of Bolivia‑specific configuration changes and custom input files.  
The table below summarises all modifications, including where each change is implemented and which custom file it depends on.

A complete run of the snakemake workflow will overwrite most of these files. After a full and successful workflow, the rule categories "Download and Filter" and "Populate Data" are done and should not overwrite the data. However, after running these rules, the custom files must manually replace the default files as decribed in the tabel below.

| Component / Adjustment | Description | File / Location |
| ------------------------ | ------------- | ------------------ |
| **Technology costs** | Updated CAPEX/OPEX for gas, diesel, biomass based on Bolivian data. Gas = 4.3 €/MWh, oil = 14.27 €/MWh, biomass = 1 €/MWh. | `custom_files/costs.csv` (replaces `resources/costs.csv`) |
| **Demand distribution & growth** | Replaces PyPSA‑Earth default demand with CNDC 2022 nodal distribution + projected growth. | `custom_files/demand_profiles.csv` (replaces `resources/demand_profiles.csv`) |
| **Hydropower inflows** | Reconstructed inflow series using seasonal CNDC patterns; reservoir storage updated from 6h → 1352h. | `custom_files/profile_hydro.nc` (replaces `resources/renewable_profiles/profile_hydro.nc`) |
| **Emission caps (NZE)** | CO₂ budget consistent with IPCC NZE‑2050; activated in NZE run‑scripts. | Implemented in `run_scripts/*_nze.py` |
| **Capacity constraints** | Max 400 MW/year new capacity; 100 MW/year geothermal; upper bounds for biomass/geothermal; yearly biomass CF constraint. | Implemented in `scripts/solve_all_networks.py` |
| **Custom grid topology** | Corrected substations and transmission lines; replaces incomplete OSM data. | `custom_files/custom_substations1.geojson` and `custom_files/custom_lines1.geojson` (referenced in `config.yaml`) |
| **Power plant database** | Updated 2022 CNDC power plant list; includes solar/wind shells and extendable hydro + geothermal potentials. | `custom_files/custom_powerplants.csv` (placed in `data/`) |

## 5) Prepare Before Scenario Runs

By cloning this repository, the custom files above are available.

Changes to the config.yaml-file and the model compared to PyPSA-Earth v.0.3.0 should remain as in this repository.

Before each scenario run, ensure that the `networks/` folder is cleared. PyPSA‑Earth regenerates all required files through the snakemake workflow.

Then run:

```bash
snakemake -j 1 solve_all_networks
```

## 6) Scenario Runs

### 6.1 Main scenarios runs

After a successful installation and configuration of PyPSA-Earth-BO, you are ready to run the different scenarios. These are ready to run, and the results will appear after the run in their respective results folders as described in the run scripts.

To generate results the run scripts need a complete network file `networks/elec_s_all_ec_lcopt_Co2L-1H.nc` (all nodes scenarios) or `networks/elec_s_4_ec_lcopt_Co2L-1H.nc` (4 nodes scenario) to run. By completing the snakemake workflow, this file should appear in the `netwoks/` folder.

| Scenario | Run Script |
| ------ | ------------- |
| Base | `run_scrips/run_base.py` |
| Base NZE | `run_scrips/run_base_nze.py` |
| Sudden Cost | `run_scrips/run_sudden.py` |
| Sudden Cost NZE | `run_scrips/run_sudden_nze.py` |
| Gradual Cost | `run_scrips/run_gradual.py` |
| Gradual Cost NZE | `run_scrips/run_gradual_nze.py` |

### 6.2 Sensitivity Runs

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

## 8) Analyze Results

The following Jupyter Notebooks are included to replicate the analysis and plots from the paper.

```bash
analysis.ipynb
plots.ipynb
plots_gas.ipynb
plots_costs.ipynb
plots_discount.ipynb
```
