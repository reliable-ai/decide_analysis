#!/bin/bash
#SBATCH --job-name=full_fertility_multiverse
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --output=slurm_output/%x-%j.out

uv run multiversum --njobs -1