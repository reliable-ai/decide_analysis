#!/bin/bash
#SBATCH --partition=yugroup
#SBATCH --job-name=invariance_check
#SBATCH --output=slurm_output/%x-%j.out

# NOTE: this script must be submitted from the `pcs_multiverse` directory
# to ensure relative paths work correctly. should be run as
# `sbatch scripts/invariance.sh`

# run the invariance check
uv run python check_order_invariance.py