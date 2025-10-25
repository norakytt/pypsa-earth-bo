import pandas as pd

def process_cost_file(target_filename: str, target_year: int):
    base_df = pd.read_csv("costs.csv")
    target_df = pd.read_csv(target_filename)

    merged_df = base_df.merge(
        target_df,
        on=["technology", "parameter"],
        how="left",
        suffixes=('', f'_{target_year}')
    )

    for col in ["value", "source", "further description", "currency_year"]:
        merged_df[col] = merged_df[f"{col}_{target_year}"]

    # Retain original values for specific technologies and parameters
    retain_mask = (
        ((merged_df["technology"] == "geothermal") & merged_df["parameter"].isin(["investment", "efficiency"])) |
        ((merged_df["technology"] == "H2 pipeline") & (merged_df["parameter"] == "efficiency")) |
        (merged_df["technology"].isin(["retrofitting I", "retrofitting II"])) |
        ((merged_df["technology"] == "central CHP") & merged_df["parameter"].isin(["investment", "lifetime", "FOM"]))
    )
    for col in ["value", "source", "further description", "currency_year"]:
        merged_df.loc[retain_mask, col] = merged_df.loc[retain_mask, f"{col}_{target_year}"].combine_first(
            base_df.loc[retain_mask, col]
        )

    # DAC from direct air capture
    dac_parameters = ["investment", "lifetime", "FOM"]
    for param in dac_parameters:
        dac_mask = (merged_df["technology"] == "DAC") & (merged_df["parameter"] == param)
        dac_row = target_df[
            (target_df["technology"] == "direct air capture") &
            (target_df["parameter"] == param)
        ]
        if not dac_row.empty:
            row = dac_row.iloc[0]
            if param == "investment":
                merged_df.loc[dac_mask, "value"] = row["value"] / 8760
                merged_df.loc[dac_mask, "unit"] = "EUR/(tCO2/a)"
            else:
                merged_df.loc[dac_mask, "value"] = row["value"]
                merged_df.loc[dac_mask, "unit"] = row["unit"]
            for col in ["source", "further description", "currency_year"]:
                merged_df.loc[dac_mask, col] = row[col]

    # Hydrogen storage override
    hst_mask = merged_df["technology"] == "hydrogen storage tank"
    for param in merged_df.loc[hst_mask, "parameter"].unique():
        hst_type1 = target_df[
            (target_df["technology"] == "hydrogen storage tank type 1") &
            (target_df["parameter"] == param)
        ]
        if not hst_type1.empty:
            row = hst_type1.iloc[0]
            mask = hst_mask & (merged_df["parameter"] == param)
            for col in ["value", "source", "further description", "currency_year", "unit"]:
                merged_df.loc[mask, col] = row[col]

    # Mark unmatched values
    merged_df.loc[merged_df["value"].isna(), "value"] = "missing"

    # Preferred units
    unit_equivalents = [
        (["EUR/kWel", "EUR/kW", "EUR/kW_e", "EUR/kW_e, 2020"], "EUR/kWel"),
        (["EUR/MWhel", "EUR/MWh", "EUR/MWh_e"], "EUR/MWhel"),
        (["EUR/MWhth", "EUR/MWh_th"], "EUR/MWhth"),
        (["EUR/kWth", "EUR/kW_th"], "EUR/MWhth"),
        (["EUR/kWhth", "EUR/kW_th"], "EUR/kWhth"),
        (["tCO2/MWth", "tCO2/MWh_th"], "tCO2/MWth"),
        (["per unit", "p.u.", "per unit charge/discharge"], "per unit"),
        (["EUR/(tCO2/a)", "EUR/(tCO2/h)"], "EUR/(tCO2/a)"),
    ]
    unit_map = {}
    for group, preferred in unit_equivalents:
        for u in group:
            unit_map[u] = preferred

    # Battery override
    battery_mask = (
        merged_df["technology"].isin(["battery storage", "battery inverter"]) &
        (merged_df["parameter"] == "investment") &
        merged_df[f"unit_{target_year}"].notna()
    )
    merged_df.loc[battery_mask, "unit"] = merged_df.loc[battery_mask, f"unit_{target_year}"]

    def resolve_unit(row):
        u1, u2 = row["unit"], row.get(f"unit_{target_year}")
        if pd.isna(u2):
            return u1
        p1 = unit_map.get(u1, u1)
        p2 = unit_map.get(u2, u2)
        if p1 == p2:
            return p1
        return f"mismatch - {u1} - {u2}"

    merged_df["unit"] = merged_df.apply(resolve_unit, axis=1)

    # Set year
    merged_df["year"] = 2025

    # Drop suffix columns
    merged_df.drop(columns=[f"{col}_{target_year}" for col in ["value", "source", "further description", "currency_year", "unit"]], inplace=True)

    # Save final file
    final_filename = f"costs_new_{target_year}.csv"
    merged_df.to_csv(final_filename, index=False)

    # Create comparison report
    original_df = base_df.copy()
    updated_df = merged_df.copy()
    original_df["value"] = pd.to_numeric(original_df["value"], errors="coerce")
    updated_df["value"] = pd.to_numeric(updated_df["value"], errors="coerce")

    comparison_df = original_df.merge(
        updated_df[["technology", "parameter", "value", "unit"]],
        on=["technology", "parameter"],
        how="left",
        suffixes=(f"_old", f"_{target_year}")
    )

    comparison_df["absolute_change"] = comparison_df[f"value_{target_year}"] - comparison_df[f"value_old"]
    comparison_df["percentage_change"] = (
        comparison_df["absolute_change"] / comparison_df[f"value_old"].replace(0, pd.NA)
    ) * 100

    report_df = comparison_df[[
        "technology", "parameter", f"unit_old",
        f"value_old", f"value_{target_year}", "absolute_change", "percentage_change"
    ]].rename(columns={
        f"unit_old": "unit",
        f"value_old": f"old_value",
        f"value_{target_year}": f"{target_year}_value"
    })

    report_filename = f"costs_change_report_{target_year}.csv"
    report_df.to_csv(report_filename, index=False)

    print(f"Finished processing {target_filename}")
    print(f"Final data: {final_filename}")
    print(f"Report saved to: {report_filename}")


target_year = 2050
process_cost_file(f"costs_{target_year}.csv", target_year)