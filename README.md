# Energy Systems Modelling: Extreme Events in Highly Renewable Networks
This repository contains the materials and scripts for a research project investigating extreme events in highly renewable energy systems using the [PyPSA](https://pypsa.org/) framework.
The study analyses extreme events under varying network configurations and provides insights into system resilience.

## Project Overview
With the growing adoption of renewable energy systems, understanding their vulnerabilities to extreme events caused by weather variability is critical.
This project reproduces and extends the findings of Grochowicz et al. (2024), analyzing the interaction between extreme events and network composition.
Key scenarios include changes in energy mix, storage capacities, and transmission limits.

## Repository Structure
The repository is organized as follows:
├── figures/ # Contains all figures generated during the project
├── scripts/ # Python scripts used to set up and simulate various scenarios
│ ├── scenario1.py
│ ├── scenario2.py
│ └── run_all.sh # Bash script for server-based batch processing
├── networks/ # Network data used in the project
│ ├── sample/ # Solved and unsolved base networks from Grochowicz et al. (2024)
│ └── output/ # Networks generated and analyzed during the project
├── README.md # Project documentation (this file) └── report/ # Final project report in PDF format


## Key Scenarios
The study investigates six key scenarios to evaluate the system's response to various configurations:
1. **Base Scenario Network**: Baseline network taken from Grochowicz et al. (2024).
2. **Changed Snapshot**: Specific extreme event periods removed to analyze cost redistribution.
3. **Changed Energy Mix**: Renewable shares adjusted to optimal levels (e.g., 60% wind, 30% solar).
4. **Storage Extremes**: Storage capacity scaled up and down to evaluate temporal balancing effects.
5. **Transmission Extremes**: Transmission capacity scaled to explore spatial balancing dynamics.
6. **Combined Scenarios**: Interactions between storage, transmission, and energy mix.

## Usage Instructions
1. Clone the repository:
      git clone https://github.com/guthibbot/RD_EnergySystemModeling.git
      cd RD_EnergySystemModeling
2. Install the python environment:
      mamba env create -f env.yml
4. Choose the scripts to run or run them all using the bash file:
      python scripts/EXAMPLE.py
      bash scripts/sbatch.sh

## Results
The project outputs include:
- **Figures**: illustrating system dynamics and extreme events (located in the figures/ folder).
- **Networks**: Solved networks with modified configurations (available at https://aarhusuniversitet-my.sharepoint.com/:f:/g/personal/au579459_uni_au_dk/Ej13MIQqfIBCoYuQkP6gV6ABaYEyEjrcOhU1VKu2eyHBRg?e=jSy7RR).
- **Report**: Comprehensive findings and analyses in the project report.
- **References**: Key references include: Grochowicz et al. (2024), "Using power system modelling outputs to identify weather-induced extreme events in highly renewable systems."

## Acknowledgments
This project was conducted as part of the Research & Development initiatives at Aarhus University
Special thanks are extended to Professor Alexander Kies at Aarhus University for his invaluable supervision of this project.

