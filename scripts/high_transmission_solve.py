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
log_file_path = f"{origin_path}/high_transmission.log"
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

    #network.snapshots = network.snapshots[:168]
    network.lines['expandable'] = True
    network.lines['capital_cost'] *= 0.1
    network.lines['s_nom'] *= 5
    network.lines['s_nom_min'] = network.lines['s_nom']

    network.links['expandable'] = True
    network.links['capital_cost'] *= 0.1
    network.links['p_nom'] *= 5
    network.links['p_nom_min'] = network.links['p_nom']

    # Step 5: Solve only for the remaining snapshots with custom constraints
    network.optimize(
        solver_name='gurobi',
        solver_options=kwargs
    )

    # Step 6: Export modified network
    output_filename = os.path.join(output_directory, os.path.basename(network_file).replace(".nc", "_HT_solved.nc"))
    network.export_to_netcdf(output_filename)
    logger.info(f"Solved and saved modified network to {output_filename}")

logger.info("Script completed.")