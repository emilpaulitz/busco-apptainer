# lib.sh - shared per-user configuration for every BUSCO HPC script.
#
# Sourced by script bodies (real shell; unlike #SBATCH directives, bodies do
# expand variables). Zero-edit default for any user; override anything via
# the environment, e.g.:
#   BUSCO_WORK=/work/paulitz/busco2 BUSCO_CPUS=32 submit.sh scripts/run_busco.sbatch
#
# Contract tested by tests/test_lib_sh.py (ticket 006).

# Where am I? Works when sourced from the repo or from the /work-staged copy.
_LIB_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Repo root / staged build root. submit.sh overrides this to
# $BUSCO_WORK/build so compute nodes never read /home (AGENTS.md).
BUSCO_REPO_ROOT=${BUSCO_REPO_ROOT:-$(dirname "$_LIB_DIR")}

# Root of this user's BUSCO work area on /work (per-user; no group /work).
BUSCO_WORK=${BUSCO_WORK:-/work/$(id -un)/busco}

# Derived layout (override individually if needed).
BUSCO_SIF=${BUSCO_SIF:-$BUSCO_WORK/busco_6.1.0.sif}
BUSCO_DOWNLOADS=${BUSCO_DOWNLOADS:-$BUSCO_WORK/downloads}
BUSCO_RESULTS=${BUSCO_RESULTS:-$BUSCO_WORK/results}
BUSCO_CHUNKS=${BUSCO_CHUNKS:-$BUSCO_WORK/chunks}
BUSCO_LOGS=${BUSCO_LOGS:-$BUSCO_WORK/logs}
BUSCO_SEQ=${BUSCO_SEQ:-$BUSCO_WORK/all_seqs}

# Group-shared input data (staging copies from here to /work on the login node).
BUSCO_INPUT_DIR=${BUSCO_INPUT_DIR:-}

# Compute nodes have no direct egress; docker:// bootstraps, curl and conda
# need this proxy (AGENTS.md). Harmless on the login node.
BUSCO_PROXY=${BUSCO_PROXY:-}

# Run knobs.
BUSCO_CPUS=${BUSCO_CPUS:-8}                   # busco -c (and --cpus-per-task via submit.sh)
# Empty default -> jobs run --auto-lineage-euk (auto-pick within eukaryote
# datasets, ticket 011). Setting it selects an explicit lineage instead
# (both download missing datasets on demand, ticket 013).
BUSCO_LINEAGE=${BUSCO_LINEAGE:-}
BUSCO_PARTITION=${BUSCO_PARTITION:-all}       # injected as sbatch --partition
BUSCO_ARRAY_LIMIT=${BUSCO_ARRAY_LIMIT:-}      # optional %limit on auto --array
