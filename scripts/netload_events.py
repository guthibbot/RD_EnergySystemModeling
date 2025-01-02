import pandas as pd
import numpy as np
import pypsa
import os
from typing import NamedTuple, Optional

if __name__ == "__main__":
    # Set the folder where your network files are stored
    network_folder = os.getenv("NETWORK_FOLDER")
    #network_folder = "networks/outputs/solved"
    network_files = [f for f in os.listdir(network_folder) if f.endswith(".nc")]

    # Dictionary to store peak week info for each network file (year)
    peak_weeks = {}

    # Loop over each network file (representing a year)
    for filename in network_files:
        n = pypsa.Network(os.path.join(network_folder, filename))

        # Calculate net load (load - renewable generation)
        renewable_generation = n.generators_t.p.sum(axis=1)
        total_load = n.loads_t.p.sum(axis=1)
        net_load = total_load - renewable_generation

        # Ensure positive net load only (optional)
        #net_load = net_load[net_load < 0]

        # Create a list to store the sum of each 168-hour window
        summed_net_loads = []

        # Define the number of hours in a 7-day period (1 week)
        window_size = 168

        # Slide through the data with a 168-hour window
        for start in range(0, len(net_load) - window_size + 1):
            # Calculate the sum for the current 168-hour window
            window_sum = net_load.iloc[start:start + window_size].sum()
            summed_net_loads.append(window_sum)

        # Find the index of the window with the highest summed net load
        max_sum_index = np.argmax(summed_net_loads)

        # Get the corresponding time period (start and end) for that window
        peak_start_time = net_load.index[max_sum_index]
        peak_end_time = net_load.index[max_sum_index + window_size - 1]

        # Store the results in a dictionary for the current file
        peak_weeks[filename] = {
            "start": peak_start_time,
            "end": peak_end_time,
            "summed_net_load": summed_net_loads[max_sum_index],
            "file_name": filename
        }

    # Convert the results into a DataFrame for better readability
    peak_weeks_df = pd.DataFrame.from_dict(peak_weeks, orient="index")

    # Save the peak week information to a CSV file
    peak_weeks_df.to_csv(f"{network_folder}/netload_events.csv", index=False)
