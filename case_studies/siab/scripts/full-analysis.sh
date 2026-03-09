#!/bin/bash
#SBATCH --partition=epurdom
#SBATCH --cpus-per-task=32
#SBATCH --job-name=full_multiverse_analysis
#SBATCH --output=slurm_output/%x-%j.out

# NOTE: this script must be submitted from the `pcs_multiverse` directory
# to ensure relative paths work correctly. should be run as
# `sbatch scripts/full-analysis.sh`

# exit immediately if any command fails
set -e

# load passphrase from .env
set -a
source .env
set +a

# create a temporary file to hold the data (only readable by current user)
TEMP_DATA=$(mktemp)
chmod 600 "$TEMP_DATA"

# ensure cleanup happens even if script fails or is interrupted
trap "rm -f $TEMP_DATA" EXIT

# decrypt once before parallel execution
gpg --batch --pinentry-mode loopback --passphrase "$GPG_PASSPHRASE" \
    --decrypt ../encrypted-data/siab_data.txt.gpg > "$TEMP_DATA"

# export the path so child processes can find it
export DECRYPTED_DATA_PATH="$TEMP_DATA"

# run the parallel analysis
uv run multiversum --njobs -1

# clean up by removing the temporary decrypted data file ensuring security
rm -f "$TEMP_DATA"