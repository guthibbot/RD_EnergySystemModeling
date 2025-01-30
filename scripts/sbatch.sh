#sbatch run_python_job.sh

# Python_job.sh
#!/bin/bash
#SBATCH --job-name=python_job         # Job name
#SBATCH --output=python_job_output.log # Output log file
#SBATCH --error=python_job_error.log   # Error log file
#SBATCH --ntasks=1                     # Number of tasks (usually 1 for a Python script)
#SBATCH --cpus-per-task=4              # Number of CPU cores per task
#SBATCH --mem=16G                      # Total memory per node
#SBATCH --time=02:00:00                # Time limit hh:mm:ss
#SBATCH --partition=q64                # Partition name


# Optional: Load modules or activate environment
#module load python
source /work/RandD/miniforge3/etc/profile.d/conda.sh
export PATH=/work/RandD/miniforge3/bin:$PATH
conda activate RD_env                   # For Conda environment
export GRB_LICENSE_FILE=/work/RandD/gurobi.lic

# Run the Python script
python /work/RandD/scripts/mix_change_solve.py
