import sys
import os
import logging
import pypsa
import pandas as pd
import glob
import subprocess
import numpy as np

origin_path = "RandD/networks/sample/unsolved"

# Set up logging
log_file_path = f"{origin_path}/mix_change.log"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", handlers=[
    logging.FileHandler(log_file_path, mode="w"),  # 'w' to overwrite each run
    logging.StreamHandler(sys.stdout)              # Print to console as well
])
logger = logging.getLogger()

# Parameters for the optimization solver
kwargs = {
    "threads": 0,
    "method": 2,  # barrier
    "crossover": 0,
    "BarConvTol": 1.e-5,
    "FeasibilityTol": 1.e-4,
    "OptimalityTol": 1.e-4,
    "Seed": 123,
    "AggFill": 0,
    "PreDual": 0,
    "GURO_PAR_BARDENSETHRESH": 200
}

# Step 2: Set up output directory for solved networks
output_directory = "RandD/networks/outputs/solved"
os.makedirs(output_directory, exist_ok=True)

# Define fractions for load that should be met by wind and solar generation
wind_fraction = 0.6  # 60% of load should be met by wind
solar_fraction = 0.4  # 40% of load should be met by solar

def wind_generation_constraint(network, snapshots):
    # Calculate total load across all snapshots
    total_load_value = network.loads_t.p_set.sum()

    # Calculate total wind generation by summing onwind, offwind-dc, and offwind-ac generators
    wind_generators = network.generators.index[
        network.generators.carrier.isin(['onwind', 'offwind-dc', 'offwind-ac'])
    ]

    # Total wind generation across specified snapshots
    wind_generation = network.model['Generator-p'].loc[snapshots, wind_generators].sum()

    # Add the constraint: wind generation >= wind_fraction * total load
    network.model.add_constraints(
        wind_generation >= wind_fraction * total_load_value,
        name="wind_generation_constraint"
    )

# Function to add wind and solar generation constraints per snapshot
def solar_generation_constraint(network, snapshots):
    # Calculate the total load for this snapshot
    total_load = network.loads_t.p_set.sum()

    # Solar generation constraint
    solar_generators = network.generators.index[
        network.generators.carrier == 'solar'
    ]
    solar_generation = network.model['Generator-p'].loc[snapshots, solar_generators].sum()

    # Add solar generation constraint for this snapshot
    network.model.add_constraints(
        solar_generation >= solar_fraction * total_load,
        name="solar_generation_constraint"
    )

#
# # Function to add wind and solar generation constraints per snapshot
# def wind_generation_constraint(network, snapshots):
#     # Loop through each snapshot to apply constraints per snapshot
#     for snapshot in snapshots:
#         # Calculate the total load for this snapshot
#         total_load_snapshot = network.loads_t.p_set.loc[snapshot].sum()
#
#         # Wind generation constraint
#         wind_generators = network.generators.index[
#             network.generators.carrier.isin(['onwind', 'offwind-dc', 'offwind-ac'])
#         ]
#         wind_generation_snapshot = network.model['Generator-p'].loc[snapshot, wind_generators].sum()
#
#         # Add wind generation constraint for this snapshot
#         network.model.add_constraints(
#             wind_generation_snapshot >= wind_fraction * total_load_snapshots,
#             name=f"wind_generation_constraint_{snapshot}"
#         )

# # Function to add wind and solar generation constraints per snapshot
# def solar_generation_constraint(network, snapshots):
#     # Loop through each snapshot to apply constraints per snapshot
#     for snapshot in snapshots:
#         # Calculate the total load for this snapshot
#         total_load_snapshot = network.loads_t.p_set.loc[snapshot].sum()
#
#         # Solar generation constraint
#         solar_generators = network.generators.index[
#             network.generators.carrier == 'solar'
#         ]
#         solar_generation_snapshot = network.model['Generator-p'].loc[snapshot, solar_generators].sum()
#
#         # Add solar generation constraint for this snapshot
#         network.model.add_constraints(
#             solar_generation_snapshot >= solar_fraction * total_load_snapshot,
#             name=f"solar_generation_constraint_{snapshot}"
#         )

# def extra_functionalities(n, snapshots):
#     wind_generation_constraint(network, snapshots)
#     #solar_generation_constraint(network, snapshots)

# Process each network file in the "networks/sample" folder
network_files = glob.glob(f"{origin_path}/*.nc")

for network_file in network_files:
    logger.info(f"Processing {network_file}...")

    # Load the network
    network = pypsa.Network(network_file)

    # Drop all generators that are not wind or solar
    #network.generators = network.generators[network.generators.carrier.isin(['onwind', 'offwind-dc', 'offwind-ac', 'solar'])]

    network.snapshots = network.snapshots[:168]
    # Calculate the total load across all snapshots
    total_load = network.loads_t.p_set.sum().sum()
    # Set the target solar generation to be 40% of the total load
    solar_fraction = 0.3
    target_generation_solar = solar_fraction * total_load
    # Define solar generation attribute and set it for solar generators
    network.carriers['generation_solar'] = 0.0
    network.carriers.at['solar', 'generation_solar'] = 1.0  # Assuming 'solar' is the carrier for solar generators
    # Add a global constraint for solar generation
    network.add("GlobalConstraint",
                "TotalSolarPVGeneration",
                type="primary_energy",
                carrier_attribute="generation_solar",
                sense=">",  # Use '=' to enforce the exact target
                constant=target_generation_solar)

    # Set the target wind generation to be a specified fraction of the total load (e.g., 40%)
    wind_fraction = 0.6
    target_generation_wind = wind_fraction * total_load
    # Define wind generation attribute and set it for wind generators
    network.carriers['generation_wind'] = 0.0  # Initialize the attribute
    network.carriers.at['onwind', 'generation_wind'] = 1.0
    network.carriers.at['offwind-dc', 'generation_wind'] = 1.0
    network.carriers.at['offwind-ac', 'generation_wind'] = 1.0
    # Add a global constraint for wind generation
    network.add("GlobalConstraint",
                "TotalWindGeneration",
                type="primary_energy",
                carrier_attribute="generation_wind",
                sense=">",  # Use '=' to enforce the exact target if desired
                constant=target_generation_wind)


    # Step 5: Solve only for the remaining snapshots with custom constraints
    network.optimize(
        solver_name='gurobi',
        #snapshots = network.snapshots[:168],
        #snapshots=network.snapshots[network.snapshots.month == 1],  # Adjust snapshots as needed
        #extra_functionality=extra_functionalities,  # Pass constraint functions here
        solver_options=kwargs
    )

    # Step 6: Export modified network
    output_filename = os.path.join(output_directory, os.path.basename(network_file).replace(".nc", "_MC_solved.nc"))
    network.export_to_netcdf(output_filename)
    logger.info(f"Solved and saved modified network to {output_filename}")

logger.info("Script completed.")












# import pypsa
# import pandas as pd
# import glob
# import os
# import subprocess
#
# # Parameters for the optimization solver
# kwargs = {
#     "threads": 0,
#     "method": 2,  # barrier
#     "crossover": 0,
#     "BarConvTol": 1.e-5,
#     "FeasibilityTol": 1.e-4,
#     "OptimalityTol": 1.e-4,
#     "Seed": 123,
#     "AggFill": 0,
#     "PreDual": 0,
#     "GURO_PAR_BARDENSETHRESH": 200
# }
#
# # Step 2: Set up output directory for solved networks
# output_directory = "networks/outputs/solved"
# os.makedirs(output_directory, exist_ok=True)
#
# # Step 3: Process each network file in the "networks/sample" folder
# network_files = glob.glob("networks/sample/*.nc")
#
# # Define the fraction of load that should be met by wind generation
# wind_fraction = 0.6  # 60% of load should be met by wind
# solar_fraction = 1 - wind_fraction
#
# # Function to add a custom constraint for wind generation share per snapshot
# def add_wind_generation_constraint(network, snapshots):
#     # Loop through each snapshot to apply the constraint per snapshot
#     for snapshot in snapshots:
#         # Total load for the specific snapshot
#         total_load_snapshot = network.loads_t.p_set.loc[snapshot].sum()
#
#         # Total wind generation for the specific snapshot
#         wind_generators = network.generators.index[
#             network.generators.carrier.isin(['onwind', 'offwind-dc', 'offwind-ac'])
#         ]
#         wind_generation_snapshot = network.model['Generator-p'].loc[snapshot, wind_generators].sum()
#
#         # Apply the constraint for this snapshot with a unique name
#         network.model.add_constraints(
#             wind_generation_snapshot >= wind_fraction * total_load_snapshot,
#             name=f"wind_generation_constraint_{snapshot}"
#         )
#
# # Function to add a custom constraint for wind generation share per snapshot
# def add_solar_generation_constraint(network, snapshots):
#     # Loop through each snapshot to apply the constraint per snapshot
#     for snapshot in snapshots:
#         # Total load for the specific snapshot
#         total_load_snapshot = network.loads_t.p_set.loc[snapshot].sum()
#
#         # Total wind generation for the specific snapshot
#         wind_generators = network.generators.index[
#             network.generators.carrier.isin(['onwind', 'offwind-dc', 'offwind-ac'])
#         ]
#         wind_generation_snapshot = network.model['Generator-p'].loc[snapshot, wind_generators].sum()
#
#         # Apply the constraint for this snapshot with a unique name
#         network.model.add_constraints(
#             wind_generation_snapshot >= wind_fraction * total_load_snapshot,
#             name=f"wind_generation_constraint_{snapshot}"
#         )
#
# # # Function to add a custom constraint for wind generation share
# # def add_wind_generation_constraint(network, snapshots):
# #     # Calculate total load across all snapshots
# #     total_load_value = network.loads_t.p_set.sum(axis=1) #.sum()
# #
# #     # Calculate total wind generation by summing onwind, offwind-dc, and offwind-ac generators
# #     wind_generators = network.generators.index[
# #         network.generators.carrier.isin(['onwind', 'offwind-dc', 'offwind-ac'])
# #     ]
# #
# #     # Total wind generation across specified snapshots
# #     wind_generation = network.model['Generator-p'].loc[snapshots, wind_generators].sum(axis=1) #.sum()
# #
# #     # Add the constraint: wind generation >= wind_fraction * total load
# #     network.model.add_constraints(
# #         wind_generation >= wind_fraction * total_load_value,
# #         name="wind_generation_constraint"
# #     )
#
#
# for network_file in network_files:
#     print(f"Processing {network_file}...")
#
#     # Load the network
#     network = pypsa.Network(network_file)
#
#     # Step 5: Solve only for the remaining snapshots with the custom constraint
#     network.optimize(
#         solver_name='gurobi',
#         snapshots=network.snapshots[network.snapshots.month == 1],
#         extra_functionality=add_wind_generation_constraint,
#         solver_options = kwargs
#         )
#
#     # Step 6: Export modified network
#     output_filename = os.path.join(output_directory, os.path.basename(network_file).replace(".nc", "_MC_solved.nc"))
#     network.export_to_netcdf(output_filename)
#     print(f"Solved and saved modified network to {output_filename}")
