#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --job-name=busco
#
# run_busco.sbatch - single-genome BUSCO run
# Submit via scripts/submit.sh, which injects the per-user
# --chdir/--output and stages this script to $BUSCO_WORK/build:
#
#   submit.sh scripts/run_busco.sbatch /work/$USER/busco/all_seqs/GENOME.fa

set -euo pipefail

LIB="${BUSCO_LIB:-$(dirname "$(readlink -f "$0")")/lib.sh}"
# shellcheck source=lib.sh
. "$LIB"

INPUT=${1:-}
if [ -z "$INPUT" ] || [ ! -f "$INPUT" ]; then
    echo "ERROR: input FASTA not found or not given: '$INPUT'" >&2
    echo "usage: submit.sh scripts/run_busco.sbatch <staged .fa on /work>" >&2
    exit 1
fi
BASE=$(basename "$INPUT")

export https_proxy=${https_proxy:-$BUSCO_PROXY}
export http_proxy=${http_proxy:-$https_proxy}

if [ -z "$BUSCO_LINEAGE" ]; then
    # Auto-pick the best eukaryote lineage per genome
    set -- --auto-lineage-euk
    MODE=autolineage-euk
else
    # Explicit lineage (set via "busco -l")
    set -- -l "$BUSCO_LINEAGE"
    MODE="explicit:$BUSCO_LINEAGE"
fi

# Reruns never overwrite, each submission gets its own dir.
OUT=$BUSCO_RESULTS/single/job_${SLURM_JOB_ID:-0}
mkdir -p "$OUT"
# requeue edge (same job id): relocate an existing run dir, never delete
if [ -d "$OUT/$BASE" ]; then
    mv "$OUT/$BASE" "$OUT/$BASE.bak_$(date +%Y%m%d_%H%M%S)"
fi

echo "=== mode=$MODE input=$INPUT ==="
if ! apptainer exec --bind /work:/work "$BUSCO_SIF" busco \
        -i "$INPUT" \
        "$@" \
        -m proteins \
        -c "$BUSCO_CPUS" \
        -o "$BASE" \
        --out_path "$OUT" \
        --download_path "$BUSCO_DOWNLOADS" \
        --opt-out-run-stats; then
    echo "BUSCO_EXIT=nonzero"
    exit 1
fi

echo "=== short summary ==="
find "$OUT/$BASE" -name "short_summary.specific.*" -exec cat {} \; 2>/dev/null || true

if [ "${ACCEPTANCE:-0}" = "1" ]; then
    if grep -q "NumberFormatException" "$OUT/$BASE/logs/busco.log" 2>/dev/null; then
        echo "ACCEPTANCE FAILED: NumberFormatException present"
        exit 1
    fi
    if find "$OUT/$BASE" -name "short_summary*" | grep -q .; then
        echo "ACCEPTANCE PASSED"
    else
        echo "ACCEPTANCE FAILED: no short_summary produced"
        exit 1
    fi
fi
