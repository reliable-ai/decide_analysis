#!/bin/bash
#SBATCH --partition=epurdom
#SBATCH --cpus-per-task=32

uv run multiversum --njobs -1