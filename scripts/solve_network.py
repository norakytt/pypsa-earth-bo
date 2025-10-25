# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
"""
Solves linear optimal power flow for a network iteratively while updating
reactances.

Relevant Settings
-----------------

.. code:: yaml

    solving:
        tmpdir:
        options:
            formulation:
            clip_p_max_pu:
            load_shedding:
            noisy_costs:
            nhours:
            min_iterations:
            max_iterations:
            skip_iterations:
            track_iterations:
        solver:
            name:

.. seealso::
    Documentation of the configuration file ``config.yaml`` at
    :ref:`electricity_cf`, :ref:`solving_cf`, :ref:`plotting_cf`

Inputs
------

- ``networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}.nc``: confer :ref:`prepare`

Outputs
-------

- ``results/networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}.nc``: Solved PyPSA network including optimisation results

    .. image:: /img/results.png
        :width: 40 %

Description
-----------

Total annual system costs are minimised with PyPSA. The full formulation of the
linear optimal power flow (plus investment planning)
is provided in the
`documentation of PyPSA <https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html#linear-optimal-power-flow>`_.
The optimization is based on the ``pyomo=False`` setting in the :func:`network.lopf` and  :func:`pypsa.linopf.ilopf` function.
Additionally, some extra constraints specified in :mod:`prepare_network` are added.

Solving the network in multiple iterations is motivated through the dependence of transmission line capacities and impedances on values of corresponding flows.
As lines are expanded their electrical parameters change, which renders the optimisation bilinear even if the power flow
equations are linearized.
To retain the computational advantage of continuous linear programming, a sequential linear programming technique
is used, where in between iterations the line impedances are updated.
Details (and errors made through this heuristic) are discussed in the paper

- Fabian Neumann and Tom Brown. `Heuristics for Transmission Expansion Planning in Low-Carbon Energy System Models <https://arxiv.org/abs/1907.10548>`_), *16th International Conference on the European Energy Market*, 2019. `arXiv:1907.10548 <https://arxiv.org/abs/1907.10548>`_.

.. warning::
    Capital costs of existing network components are not included in the objective function,
    since for the optimisation problem they are just a constant term (no influence on optimal result).

    Therefore, these capital costs are not included in ``network.objective``!

    If you want to calculate the full total annual system costs add these to the objective value.

.. tip::
    The rule :mod:`solve_all_networks` runs
    for all ``scenario`` s in the configuration file
    the rule :mod:`solve_network`.
"""
import logging
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
from _helpers import configure_logging, create_logger
from pypsa.descriptors import get_switchable_as_dense as get_as_dense
from pypsa.linopf import (
    define_constraints,
    define_variables,
    get_var,
    ilopf,
    join_exprs,
    linexpr,
    network_lopf,
)

logger = create_logger(__name__)


def prepare_network(n, solve_opts):
    if "clip_p_max_pu" in solve_opts:
        for df in (n.generators_t.p_max_pu, n.storage_units_t.inflow):
            df.where(df > solve_opts["clip_p_max_pu"], other=0.0, inplace=True)

    load_shedding = solve_opts.get("load_shedding")
    if load_shedding:
        n.add("Carrier", "Load")
        buses_i = n.buses.query("carrier == 'AC'").index
        if not np.isscalar(load_shedding):
            load_shedding = 8e3 #22 #8e3  # Eur/kWh
        # intersect between macroeconomic and surveybased
        # willingness to pay
        # http://journal.frontiersin.org/article/10.3389/fenrg.2015.00055/full)
        # 1e2 is practical relevant, 8e3 good for debugging
        n.madd(
            "Generator",
            buses_i,
            " load",
            bus=buses_i,
            carrier="load",
            sign=1e-3,  # Adjust sign to measure p and p_nom in kW instead of MW
            marginal_cost= 1e2, # Eur/kWh
            p_nom=1e9,  # kW
        )

    if solve_opts.get("noisy_costs"):
        for t in n.iterate_components(n.one_port_components):
            # TODO: uncomment out to and test noisy_cost (makes solution unique)
            # if 'capital_cost' in t.df:
            #    t.df['capital_cost'] += 1e1 + 2.*(np.random.random(len(t.df)) - 0.5)
            if "marginal_cost" in t.df:
                t.df["marginal_cost"] += 1e-2 + 2e-3 * (
                    np.random.random(len(t.df)) - 0.5
                )

        for t in n.iterate_components(["Line", "Link"]):
            t.df["capital_cost"] += (
                1e-1 + 2e-2 * (np.random.random(len(t.df)) - 0.5)
            ) * t.df["length"]

    if solve_opts.get("nhours"):
        nhours = solve_opts["nhours"]
        n.set_snapshots(n.snapshots[:nhours])
        n.snapshot_weightings[:] = 8760.0 / nhours

    return n


def add_CCL_constraints(n, config):
    agg_p_nom_limits = config["electricity"].get("agg_p_nom_limits")

    try:
        agg_p_nom_minmax = pd.read_csv(agg_p_nom_limits, index_col=list(range(2)))
    except IOError:
        logger.exception(
            "Need to specify the path to a .csv file containing "
            "aggregate capacity limits per country in "
            "config['electricity']['agg_p_nom_limit']."
        )
    logger.info(
        "Adding per carrier generation capacity constraints for " "individual countries"
    )

    gen_country = n.generators.bus.map(n.buses.country)
    # cc means country and carrier
    p_nom_per_cc = (
        pd.DataFrame(
            {
                "p_nom": linexpr((1, get_var(n, "Generator", "p_nom"))),
                "country": gen_country,
                "carrier": n.generators.carrier,
            }
        )
        .dropna(subset=["p_nom"])
        .groupby(["country", "carrier"])
        .p_nom.apply(join_exprs)
    )
    minimum = agg_p_nom_minmax["min"].dropna()
    if not minimum.empty:
        minconstraint = define_constraints(
            n, p_nom_per_cc[minimum.index], ">=", minimum, "agg_p_nom", "min"
        )
    maximum = agg_p_nom_minmax["max"].dropna()
    if not maximum.empty:
        maxconstraint = define_constraints(
            n, p_nom_per_cc[maximum.index], "<=", maximum, "agg_p_nom", "max"
        )


def add_EQ_constraints(n, o, scaling=1e-1):
    float_regex = "[0-9]*\.?[0-9]+"
    level = float(re.findall(float_regex, o)[0])
    if o[-1] == "c":
        ggrouper = n.generators.bus.map(n.buses.country)
        lgrouper = n.loads.bus.map(n.buses.country)
        sgrouper = n.storage_units.bus.map(n.buses.country)
    else:
        ggrouper = n.generators.bus
        lgrouper = n.loads.bus
        sgrouper = n.storage_units.bus
    load = (
        n.snapshot_weightings.generators
        @ n.loads_t.p_set.groupby(lgrouper, axis=1).sum()
    )
    inflow = (
        n.snapshot_weightings.stores
        @ n.storage_units_t.inflow.groupby(sgrouper, axis=1).sum()
    )
    inflow = inflow.reindex(load.index).fillna(0.0)
    rhs = scaling * (level * load - inflow)
    lhs_gen = (
        linexpr(
            (n.snapshot_weightings.generators * scaling, get_var(n, "Generator", "p").T)
        )
        .T.groupby(ggrouper, axis=1)
        .apply(join_exprs)
    )
    lhs_spill = (
        linexpr(
            (
                -n.snapshot_weightings.stores * scaling,
                get_var(n, "StorageUnit", "spill").T,
            )
        )
        .T.groupby(sgrouper, axis=1)
        .apply(join_exprs)
    )
    lhs_spill = lhs_spill.reindex(lhs_gen.index).fillna("")
    lhs = lhs_gen + lhs_spill
    define_constraints(n, lhs, ">=", rhs, "equity", "min")


def add_BAU_constraints(n, config):
    ext_c = n.generators.query("p_nom_extendable").carrier.unique()
    mincaps = pd.Series(
        config["electricity"].get("BAU_mincapacities", {key: 0 for key in ext_c})
    )
    lhs = (
        linexpr((1, get_var(n, "Generator", "p_nom")))
        .groupby(n.generators.carrier)
        .apply(join_exprs)
    )
    define_constraints(n, lhs, ">=", mincaps[lhs.index], "Carrier", "bau_mincaps")

    maxcaps = pd.Series(
        config["electricity"].get("BAU_maxcapacities", {key: np.inf for key in ext_c})
    )
    lhs = (
        linexpr((1, get_var(n, "Generator", "p_nom")))
        .groupby(n.generators.carrier)
        .apply(join_exprs)
    )
    define_constraints(n, lhs, "<=", maxcaps[lhs.index], "Carrier", "bau_maxcaps")


def add_SAFE_constraints(n, config):
    peakdemand = (
        1.0 + config["electricity"]["SAFE_reservemargin"]
    ) * n.loads_t.p_set.sum(axis=1).max()
    conv_techs = config["plotting"]["conv_techs"]
    exist_conv_caps = n.generators.query(
        "~p_nom_extendable & carrier in @conv_techs"
    ).p_nom.sum()
    ext_gens_i = n.generators.query("carrier in @conv_techs & p_nom_extendable").index
    lhs = linexpr((1, get_var(n, "Generator", "p_nom")[ext_gens_i])).sum()
    rhs = peakdemand - exist_conv_caps
    define_constraints(n, lhs, ">=", rhs, "Safe", "mintotalcap")


def add_operational_reserve_margin_constraint(n, config):
    reserve_config = config["electricity"]["operational_reserve"]
    EPSILON_LOAD = reserve_config["epsilon_load"]
    EPSILON_VRES = reserve_config["epsilon_vres"]
    CONTINGENCY = reserve_config["contingency"]

    # Reserve Variables
    reserve = get_var(n, "Generator", "r")
    lhs = linexpr((1, reserve)).sum(1)

    # Share of extendable renewable capacities
    ext_i = n.generators.query("p_nom_extendable").index
    vres_i = n.generators_t.p_max_pu.columns
    if not ext_i.empty and not vres_i.empty:
        capacity_factor = n.generators_t.p_max_pu[vres_i.intersection(ext_i)]
        renewable_capacity_variables = get_var(n, "Generator", "p_nom")[
            vres_i.intersection(ext_i)
        ]
        lhs += linexpr(
            (-EPSILON_VRES * capacity_factor, renewable_capacity_variables)
        ).sum(1)

    # Total demand at t
    demand = n.loads_t.p.sum(1)

    # VRES potential of non extendable generators
    capacity_factor = n.generators_t.p_max_pu[vres_i.difference(ext_i)]
    renewable_capacity = n.generators.p_nom[vres_i.difference(ext_i)]
    potential = (capacity_factor * renewable_capacity).sum(1)

    # Right-hand-side
    rhs = EPSILON_LOAD * demand + EPSILON_VRES * potential + CONTINGENCY

    define_constraints(n, lhs, ">=", rhs, "Reserve margin")


def update_capacity_constraint(n):
    gen_i = n.generators.index
    ext_i = n.generators.query("p_nom_extendable").index
    fix_i = n.generators.query("not p_nom_extendable").index

    dispatch = get_var(n, "Generator", "p")
    reserve = get_var(n, "Generator", "r")

    capacity_fixed = n.generators.p_nom[fix_i]

    p_max_pu = get_as_dense(n, "Generator", "p_max_pu")

    lhs = linexpr((1, dispatch), (1, reserve))

    if not ext_i.empty:
        capacity_variable = get_var(n, "Generator", "p_nom")
        lhs += linexpr((-p_max_pu[ext_i], capacity_variable)).reindex(
            columns=gen_i, fill_value=""
        )

    rhs = (p_max_pu[fix_i] * capacity_fixed).reindex(columns=gen_i, fill_value=0)

    define_constraints(n, lhs, "<=", rhs, "Generators", "updated_capacity_constraint")


def add_operational_reserve_margin(n, sns, config):
    """
    Build reserve margin constraints based on the formulation given in
    https://genxproject.github.io/GenX/dev/core/#Reserves.
    """

    define_variables(n, 0, np.inf, "Generator", "r", axes=[sns, n.generators.index])

    add_operational_reserve_margin_constraint(n, config)

    update_capacity_constraint(n)


def add_battery_constraints(n):
    nodes = n.buses.index[n.buses.carrier == "battery"]
    if nodes.empty or ("Link", "p_nom") not in n.variables.index:
        return
    link_p_nom = get_var(n, "Link", "p_nom")
    lhs = linexpr(
        (1, link_p_nom[nodes + " charger"]),
        (
            -n.links.loc[nodes + " discharger", "efficiency"].values,
            link_p_nom[nodes + " discharger"].values,
        ),
    )
    define_constraints(n, lhs, "=", 0, "Link", "charger_ratio")


def add_RES_constraints(n, res_share):
    lgrouper = n.loads.bus.map(n.buses.country)
    ggrouper = n.generators.bus.map(n.buses.country)
    sgrouper = n.storage_units.bus.map(n.buses.country)
    cgrouper = n.links.bus0.map(n.buses.country)

    logger.warning(
        "The add_RES_constraints functionality is still work in progress. "
        "Unexpected results might be incurred, particularly if "
        "temporal clustering is applied or if an unexpected change of technologies "
        "is subject to the obtimisation."
    )

    load = (
        n.snapshot_weightings.generators
        @ n.loads_t.p_set.groupby(lgrouper, axis=1).sum()
    )

    rhs = res_share * load

    res_techs = [
        "solar",
        "onwind",
        "offwind-dc",
        "offwind-ac",
        "battery",
        "hydro",
        "ror",
    ]
    charger = ["H2 electrolysis", "battery charger"]
    discharger = ["H2 fuel cell", "battery discharger"]

    gens_i = n.generators.query("carrier in @res_techs").index
    stores_i = n.storage_units.query("carrier in @res_techs").index
    charger_i = n.links.query("carrier in @charger").index
    discharger_i = n.links.query("carrier in @discharger").index

    # Generators
    lhs_gen = (
        linexpr(
            (n.snapshot_weightings.generators, get_var(n, "Generator", "p")[gens_i].T)
        )
        .T.groupby(ggrouper, axis=1)
        .apply(join_exprs)
    )

    # StorageUnits
    lhs_dispatch = (
        (
            linexpr(
                (
                    n.snapshot_weightings.stores,
                    get_var(n, "StorageUnit", "p_dispatch")[stores_i].T,
                )
            )
            .T.groupby(sgrouper, axis=1)
            .apply(join_exprs)
        )
        .reindex(lhs_gen.index)
        .fillna("")
    )

    lhs_store = (
        (
            linexpr(
                (
                    -n.snapshot_weightings.stores,
                    get_var(n, "StorageUnit", "p_store")[stores_i].T,
                )
            )
            .T.groupby(sgrouper, axis=1)
            .apply(join_exprs)
        )
        .reindex(lhs_gen.index)
        .fillna("")
    )

    # Stores (or their resp. Link components)
    # Note that the variables "p0" and "p1" currently do not exist.
    # Thus, p0 and p1 must be derived from "p" (which exists), taking into account the link efficiency.
    lhs_charge = (
        (
            linexpr(
                (
                    -n.snapshot_weightings.stores,
                    get_var(n, "Link", "p")[charger_i].T,
                )
            )
            .T.groupby(cgrouper, axis=1)
            .apply(join_exprs)
        )
        .reindex(lhs_gen.index)
        .fillna("")
    )

    lhs_discharge = (
        (
            linexpr(
                (
                    n.snapshot_weightings.stores.apply(
                        lambda r: r * n.links.loc[discharger_i].efficiency
                    ),
                    get_var(n, "Link", "p")[discharger_i],
                )
            )
            .groupby(cgrouper, axis=1)
            .apply(join_exprs)
        )
        .reindex(lhs_gen.index)
        .fillna("")
    )

    # signs of resp. terms are coded in the linexpr.
    # todo: for links (lhs_charge and lhs_discharge), account for snapshot weightings
    lhs = lhs_gen + lhs_dispatch + lhs_store + lhs_charge + lhs_discharge

    define_constraints(n, lhs, "=", rhs, "RES share")

def new_capacity_constraint(n):
    solar_i = n.generators.query("carrier == 'solar'").index
    onwind_i = n.generators.query("carrier == 'onwind'").index
    biomass_i = n.generators.query("carrier == 'biomass'").index
    ror_i = n.generators.query("carrier == 'ror'& p_nom_extendable").index
    hydro_i = n.storage_units.query("carrier == 'hydro'").index
    geothermal_i = n.generators.query("carrier == 'geothermal'").index
    ccgt_i = n.generators.query("carrier == 'CCGT'").index
    ocgt_i = n.generators.query("carrier == 'OCGT'").index
    oil_i = n.generators.query("carrier == 'oil'").index
    all_i = solar_i.append([onwind_i, biomass_i, ror_i, geothermal_i, ccgt_i, ocgt_i, oil_i])

    #print(get_var(n, "Generator", "p_nom").index)  # Likely to be strings like '0 solar', '1 onwind'...
    #print(all_i)  # Likely integers like 0, 1, 2, ...

    p_nom_current = get_var(n, "Generator", "p_nom")[all_i]
    #p_nom_storage = get_var(n, "StorageUnit", "p_store")[hydro_i]
    lhs = linexpr((1,p_nom_current)).sum()
    rhs = n.generators.loc[all_i,'p_nom'].sum() + 400
    define_constraints(n, lhs, '<=', rhs, 'Generator', 'new_capacity')

def new_geothermal_capacity_constraint(n):
    geothermal_i = n.generators.query("carrier == 'geothermal'").index
    p_nom_current = get_var(n, "Generator", "p_nom")[geothermal_i]
    lhs = linexpr((1,p_nom_current)).sum()
    rhs = n.generators.loc[geothermal_i,'p_nom'].sum() + 100
    define_constraints(n, lhs, '<=', rhs, 'Generator', 'new_geothermal_capacity')


def new_battery_capaity_constraint(n):
    """Adds a capacity constraint to the overall battery capacity.
    """
    battery_discharge_i = n.links.query("carrier == 'battery discharger'").index
    battery_discharge_p_nom = get_var(n, "Link", "p_nom")[battery_discharge_i]
    lhs = linexpr((1,battery_discharge_p_nom)).sum()
    rhs = 900
    define_constraints(n, lhs, "<=", rhs, "Battery", "max_discharge_capacity")

def new_battery_storage_constraint(n):
    """Adds a capacity constraint to the overall battery storage capacity.
    """
    battery_i = n.stores.query("carrier == 'battery'").index
    battery_e_nom = get_var(n, "Store", "e_nom")[battery_i]
    lhs = linexpr((1,battery_e_nom)).sum()
    rhs = 5400
    define_constraints(n, lhs, "<=", rhs, "Battery", "max_battery_capacity")

def new_biomass_total_capacity_constraint(n):
    """Adds a capacity constraint to the overall biomass capacity.
    """
    biomass_i = n.generators.query("carrier == 'biomass'").index
    biomass_p_nom = get_var(n, "Generator", "p_nom")[biomass_i]
    lhs = linexpr((1,biomass_p_nom)).sum()
    rhs = 840
    define_constraints(n, lhs, "<=", rhs, "Biomass", "max_total_capacity")

def new_geothermal_total_capacity_constraint(n):
    """Adds a capacity constraint to the overall geothermal capacity.
    """
    geothermal_i = n.generators.query("carrier == 'geothermal'").index
    geothermal_p_nom = get_var(n, "Generator", "p_nom")[geothermal_i]
    lhs = linexpr((1,geothermal_p_nom)).sum()
    rhs = 510
    define_constraints(n, lhs, "<=", rhs, "Geothermal", "max_total_capacity")

    
def apply_cp_constraints_bio(n):
    cp = 0.72
    carrier = 'biomass'
    hours_in_year = -1
    gen_indices = n.generators.query(f"carrier == '{carrier}'").index
    coeff = hours_in_year * cp
    lhs = linexpr((1, get_var(n, "Generator", "p").loc[n.snapshots[:], gen_indices]), (coeff, get_var(n, "Generator", "p_nom")[gen_indices])).sum()
    rhs = 0
    define_constraints(n, lhs, "<=", rhs, carrier, "cp_constraint")
    # gen_indices = n.generators.query(f"carrier == '{carrier}'").index
    # for i in gen_indices:
    #     lhs = linexpr((1, get_var(n, "Generator", "p").loc[:, i]), (cp,get_var(n, "Generator", "p_nom").loc[i])).sum()
    #     rhs = 0
    #     define_constraints(n, lhs, "<=", rhs, carrier, "cp_constraint")

def line_capacity_constraint(n):
    # limit s_nom to 10000 MW per line
    line_i = n.lines.index
    for i in line_i:
        lhs = linexpr((1, get_var(n, "Line", "s_nom").loc[i]))
        rhs = 1e+04
        define_constraints(n, lhs, "<=", rhs, "Line", "line_capacity_constraint")

def apply_cp_constraints_bio_monte_carlo(n):
    cp = 0.72
    carrier = 'biomass'
    gen_indices = n.generators.query(f"carrier == '{carrier}'").index
    for i in gen_indices:
        capacity_fixed = n.generators.p_nom[i]
        lhs = linexpr((1, get_var(n, "Generator", "p").loc[:, i])).sum()
        rhs = capacity_fixed * cp * 8760
        define_constraints(n, lhs, "<=", rhs, carrier, "cp_constraint")
 
 
def apply_cp_constraints_CCGT(n):
    cp = 0.64
    carrier = 'CCGT'
    hours_in_year = -1
    gen_indices = n.generators.query(f"carrier == '{carrier}'").index
    coeff = hours_in_year * cp
    lhs = linexpr((1, get_var(n, "Generator", "p").loc[n.snapshots[:], gen_indices]), (coeff, get_var(n, "Generator", "p_nom")[gen_indices])).sum()
    rhs = 0
    define_constraints(n, lhs, "<=", rhs, carrier, "cp_constraint")
   
def apply_cp_constraints_OCGT(n):
    cp = 0.64
    carrier = 'OCGT'
    hours_in_year = -1
    gen_indices = n.generators.query(f"carrier == '{carrier}'").index
    coeff = hours_in_year * cp
    lhs = linexpr((1, get_var(n, "Generator", "p").loc[n.snapshots[:], gen_indices]), (coeff, get_var(n, "Generator", "p_nom")[gen_indices])).sum()
    rhs = 0
    define_constraints(n, lhs, "<=", rhs, carrier, "cp_constraint")
   
def apply_cp_constraints_geo(n):
    cp = 0.9
    carrier = 'geothermal'
    hours_in_year = -1
    gen_indices = n.generators.query(f"carrier == '{carrier}'").index
    coeff = hours_in_year * cp
    lhs = linexpr((1, get_var(n, "Generator", "p").loc[n.snapshots[:], gen_indices]), (coeff, get_var(n, "Generator", "p_nom")[gen_indices])).sum()
    rhs = 0
    define_constraints(n, lhs, "<=", rhs, carrier, "cp_constraint")
   
def apply_cp_constraints_ror_ext(n):
    cp = 0.5
    carrier = 'ror'
    hours_in_year = -1
    gen_indices = n.generators.query(f"carrier == '{carrier}' & p_nom_extendable").index
    coeff = hours_in_year * cp
    lhs = linexpr((1, get_var(n, "Generator", "p").loc[n.snapshots[:], gen_indices]), (coeff, get_var(n, "Generator", "p_nom")[gen_indices])).sum()
    rhs = 0
    define_constraints(n, lhs, "<=", rhs, carrier, "cp_constraint")

def apply_cp_constraints_hydro_fix(n):
    cp = 0.5
    carrier = 'hydro'
    hours_in_year = 8760
    gen_indices = n.storage_units.query(f"carrier == '{carrier}'").index
    coeff = n.storage_units.loc[gen_indices, 'p_nom'] * hours_in_year * cp
    lhs = linexpr((1, get_var(n, "StorageUnit", "p_dispatch").loc[n.snapshots[:], gen_indices])).sum()
    rhs = coeff
    define_constraints(n, lhs, "<=", rhs, carrier, "cp_constraint_fix")

def apply_cp_constraints_ror_fix(n):
    cp = 0.5
    carrier = 'ror'
    hours_in_year = 8760
    gen_indices = n.generators.query(f"carrier == '{carrier}' & not p_nom_extendable").index
    coeff = n.generators.loc[gen_indices, 'p_nom'] * hours_in_year * cp
    lhs = linexpr((1, get_var(n, "Generator", "p").loc[n.snapshots[:], gen_indices])).sum()
    rhs = coeff
    define_constraints(n, lhs, "<=", rhs, carrier, "cp_constraint_fix")

def reliability_constraint_line(n, matrix):
    line_i = n.lines.index
    snapshots = n.snapshots

    for line in line_i:
        for snapshot in snapshots:
            if matrix.loc[snapshot, line] == 0.0:
                s = get_var(n, "Line", "s").loc[snapshot, line]
                lhs = linexpr((1, abs(s)))
                rhs = 0
                define_constraints(n, lhs, "=", rhs, "Line", "reliability_line_constraint")

def reliability_constraint(n, matrix):
    for carrier in n.generators[~n.generators.carrier.str.contains('load')].carrier.unique():
        gen_indices = n.generators.query(f"carrier == '{carrier}'").index
        snapshots = n.snapshots
        for gen in gen_indices:
            for snapshot in snapshots:
                if matrix.loc[snapshot, gen] == 0.0:
                    s = get_var(n, "Generator", "p").loc[snapshot, gen]
                    lhs = linexpr((1, abs(s)))
                    rhs = 0
                    define_constraints(n, lhs, "=", rhs, "Generators", "reliability_constraint")

def reliability_constraint_storage(n, matrix):
    storage_i = n.storage_units.index
    snapshots = n.snapshots
    for storage in storage_i:
        for snapshot in snapshots:
            if matrix.loc[snapshot, storage] == 0.0:
                s = get_var(n, "StorageUnit", "p_dispatch").loc[snapshot, storage]
                lhs = linexpr((1, abs(s)))
                rhs = 0
                define_constraints(n, lhs, "=", rhs, "Storage", "reliability_storage_constraint")


# line_matrix = pd.read_csv("C:/Users/noraky/Documents/Masteroppgave/pypsa-earth/matrices/lines_matrix.csv", index_col=0)
# generator_matrix = pd.read_csv("C:/Users/noraky/Documents/Masteroppgave/pypsa-earth/matrices/generators_matrix.csv", index_col=0)
# storage_unit_matrix = pd.read_csv("C:/Users/noraky/Documents/Masteroppgave/pypsa-earth/matrices/storage_units_matrix.csv", index_col=0)
# line_matrix.index = pd.to_datetime(line_matrix.index)
# generator_matrix.index = pd.to_datetime(generator_matrix.index)
# storage_unit_matrix.index = pd.to_datetime(storage_unit_matrix.index)

def extra_functionality(n, snapshots):
    """
    Collects supplementary constraints which will be passed to
    ``pypsa.linopf.network_lopf``.

    If you want to enforce additional custom constraints, this is a good location to add them.
    The arguments ``opts`` and ``snakemake.config`` are expected to be attached to the network.
    """
    opts = n.opts
    config = n.config
    if "BAU" in opts and n.generators.p_nom_extendable.any():
        add_BAU_constraints(n, config)
    if "SAFE" in opts and n.generators.p_nom_extendable.any():
        add_SAFE_constraints(n, config)
    if "CCL" in opts and n.generators.p_nom_extendable.any():
        add_CCL_constraints(n, config)
    reserve = config["electricity"].get("operational_reserve", {})
    if reserve.get("activate"):
        add_operational_reserve_margin(n, snapshots, config)
    for o in opts:
        if "RES" in o:
            res_share = float(re.findall("[0-9]*\.?[0-9]+$", o)[0])
            add_RES_constraints(n, res_share)
    for o in opts:
        if "EQ" in o:
            add_EQ_constraints(n, o)

    add_battery_constraints(n)
    new_capacity_constraint(n)
    new_geothermal_capacity_constraint(n)
    new_battery_capaity_constraint(n)
    new_battery_storage_constraint(n)
    new_biomass_total_capacity_constraint(n)
    new_geothermal_total_capacity_constraint(n)
    apply_cp_constraints_bio(n)
    #line_capacity_constraint(n)
    #apply_cp_constraints_CCGT(n)
    #apply_cp_constraints_OCGT(n)
    #apply_cp_constraints_geo(n)
    #apply_cp_constraints_ror_ext(n)
    #apply_cp_constraints_hydro_fix(n)
    #apply_cp_constraints_ror_fix(n)
    #apply_cp_constraints_bio_monte_carlo(n)
    # reliability_constraint_line(n,line_matrix)
    # reliability_constraint(n, generator_matrix)
    # reliability_constraint_storage(n, storage_unit_matrix)
    



def solve_network(n, config, opts="", **kwargs):
    solver_options = config["solving"]["solver"].copy()
    solver_name = solver_options.pop("name")
    cf_solving = config["solving"]["options"]
    track_iterations = cf_solving.get("track_iterations", False)
    min_iterations = cf_solving.get("min_iterations", 4)
    max_iterations = cf_solving.get("max_iterations", 6)

    # add to network for extra_functionality
    n.config = config
    n.opts = opts

    if cf_solving.get("skip_iterations", False):
        network_lopf(
            n,
            solver_name=solver_name,
            solver_options=solver_options,
            extra_functionality=extra_functionality,
            **kwargs,
        )
    else:
        ilopf(
            n,
            solver_name=solver_name,
            solver_options=solver_options,
            track_iterations=track_iterations,
            min_iterations=min_iterations,
            max_iterations=max_iterations,
            extra_functionality=extra_functionality,
            **kwargs,
        )
    return n


if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        snakemake = mock_snakemake(
            "solve_network",
            simpl="",
            clusters="54",
            ll="copt",
            opts="Co2L-1H",
        )
    configure_logging(snakemake)

    tmpdir = snakemake.params.solving.get("tmpdir")
    if tmpdir is not None:
        Path(tmpdir).mkdir(parents=True, exist_ok=True)
    opts = snakemake.wildcards.opts.split("-")
    solve_opts = snakemake.params.solving["options"]

    n = pypsa.Network(snakemake.input[0])
    if snakemake.params.augmented_line_connection.get("add_to_snakefile"):
        n.lines.loc[
            n.lines.index.str.contains("new"), "s_nom_min"
        ] = snakemake.params.augmented_line_connection.get("min_expansion")
    n = prepare_network(n, solve_opts)

    n = solve_network(
        n,
        config=snakemake.config,
        opts=opts,
        solver_dir=tmpdir,
        solver_logfile=snakemake.log.solver,
    )
    n.meta = dict(snakemake.config, **dict(wildcards=dict(snakemake.wildcards)))
    n.export_to_netcdf(snakemake.output[0])
