#!/bin/bash
#SBATCH --job-name=hurricane-ablation
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --output=slurm_output/%x-%j.out

# Run all ablation multiverses sequentially.
# Each ablation fixes one dimension to its default value and varies the rest.
# For SLURM to work properly, needs to be submitted from the `ablation/` directory.
#
# Usage:
#   bash run_all.sh            # sequential, all CPUs per run
#   bash run_all.sh --test     # test mode (small subset, useful for sanity checks)

set -euo pipefail

DIMS=(
    death_outliers
    damage_outliers
    femininity_calculation
    damage_transform
    model
    main_interaction
    other_predictors
    covariates
)

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-.}"

MODE_ARGS=""
if [[ "${1:-}" == "--test" ]]; then
    MODE_ARGS="--mode=test"
fi

for dim in "${DIMS[@]}"; do
    echo "=== Ablation: fixing $dim ==="
    (cd "$SCRIPT_DIR/$dim" && uv run multiversum --njobs -1 $MODE_ARGS)
    echo ""
done

echo "All ablation runs complete."
