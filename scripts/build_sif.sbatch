#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --job-name=build_sif
#
# build_sif.sbatch - build the BUSCO SIF inside a batch job (see ticket 006).
# submit.sh injects the per-user --chdir/--output and stages this script,
# build_sif.sh, busco.def and the BuscoPlacer patch to $BUSCO_WORK/build
# (because HPC compute nodes are only allowed to read from /work in batch jobs.
#
# Submit:  submit.sh scripts/build_sif.sbatch

set -euo pipefail
module purge 2>/dev/null || true

LIB="${BUSCO_LIB:-$(dirname "$(readlink -f "$0")")/lib.sh}"
# shellcheck source=lib.sh
. "$LIB"

export https_proxy=${https_proxy:-$BUSCO_PROXY}
export http_proxy=${http_proxy:-$https_proxy}

# Locate the helper next to lib.sh, NOT via $0: on this cluster sbatch runs
# the job from /var/spool/slurmd/job<id>/slurm_script, so $0 points at the
# spool copy. submit.sh stages lib.sh and build_sif.sh into the same dir.
"$(dirname "$(readlink -f "$LIB")")/build_sif.sh" rebuild
