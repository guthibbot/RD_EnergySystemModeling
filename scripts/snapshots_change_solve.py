import sys
import os
import logging
import pypsa
import pandas as pd
import glob
import subprocess
import numpy as np

# Set up logging
log_file_path = "RandD/networks/sample/solved/snapshot_change.log"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", handlers=[
    logging.FileHandler(log_file_path, mode="w"),  # 'w' to overwrite each run
    logging.StreamHandler(sys.stdout)              # Print to console as well
])
logger = logging.getLogger()

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

# Define the folder where your .nc files are located
network_folder = "./RandD/networks/sample/solved/"  # Change this to your folder path
env = os.environ.copy()
env["NETWORK_FOLDER"] = network_folder

# Step 0: Run "scripts/difficult_periods.py" to generate "difficult_periods.csv"
logger.info("Running 'RandD/scripts/difficult_periods.py' to generate 'difficult_periods.csv'")
result = subprocess.run(["python", "RandD/scripts/difficult_periods.py"], check=True, env=env, capture_output=True, text=True)
logger.info(result.stdout)  # Log stdout of the subprocess
if result.stderr:
    logger.error(result.stderr)  # Log stderr if there are errors

# Step 1: Read the CSV file with periods to exclude
exclude_periods = pd.read_csv('RandD/networks/sample/solved/difficult_periods.csv', parse_dates=['start', 'end'])

# Step 2: Set up output directory for solved networks
output_directory = "RandD/networks/outputs/solved"
os.makedirs(output_directory, exist_ok=True)

# Step 3: Process each network file in the "networks/sample" folder
network_files = glob.glob("RandD/networks/sample/unsolved/*.nc")

for network_file in network_files:
    logger.info(f"Processing {network_file}...")

    # Load the network
    n = pypsa.Network(network_file)

    # Step 4: Identify snapshots to exclude
    snapshots_to_exclude = set()

    for _, row in exclude_periods.iterrows():
        start_time = row['start'].strftime("%Y-%m-%d %H:%M:%S")  # Convert to string
        end_time = row['end'].strftime("%Y-%m-%d %H:%M:%S")      # Convert to string

        # Check if snapshots in n fall within the start and end range
        snapshots_to_exclude.update(n.snapshots[(n.snapshots >= start_time) & (n.snapshots <= end_time)])

    # Convert to list for filtering
    snapshots_to_exclude = list(snapshots_to_exclude)

    # Get the remaining snapshots
    remaining_snapshots = n.snapshots.drop(snapshots_to_exclude)

    # Check if any snapshots were actually excluded
    if set(remaining_snapshots) == set(n.snapshots):
        logger.info(f"No snapshot changes for {network_file}. Skipping optimization.")
        continue  # Skip to the next network file if no snapshots were excluded

    # Drop snapshots
    n.snapshots = n.snapshots.drop(snapshots_to_exclude)

    # Step 5: Solve
    n.optimize(solver_name='gurobi', keep_files=False, solver_options=kwargs)

    # Step 6: Export modified solved network
    output_filename = os.path.join(output_directory, os.path.basename(network_file).replace(".nc", "_SC_solved.nc"))
    n.export_to_netcdf(output_filename)
    logger.info(f"Solved and saved modified network to {output_filename}")

logger.info("Script completed.")
