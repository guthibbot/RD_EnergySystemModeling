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

# Process each network file in the "networks/sample" folder
network_files = glob.glob(f"{origin_path}/*.nc")

for network_file in network_files:
    logger.info(f"Processing {network_file}...")

    # Load the network
    network = pypsa.Network(network_file)

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
        #snapshots = network.snapshots[0:168],
        #snapshots=network.snapshots[network.snapshots.month == 1],  # Adjust snapshots as needed
        #extra_functionality=extra_functionalities,  # Pass constraint functions here
        solver_options=kwargs
    )

    # Step 6: Export modified network
    output_filename = os.path.join(output_directory, os.path.basename(network_file).replace(".nc", "_MC_solved.nc"))
    network.export_to_netcdf(output_filename)
    logger.info(f"Solved and saved modified network to {output_filename}")

logger.info("Script completed.")
