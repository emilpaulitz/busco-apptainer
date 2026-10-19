#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --job-name=busco_array
#
# run_busco_array.sbatch - batch-run staged genomes as a SLURM array
# One array task per chunk dir of staged .fa files:

# Resume-safe: genomes with an existing short_summary are skipped,
# so failed tasks can be resubmitted with --array=0,5 etc.
#
# logs per array task: $BUSCO_LOGS/busco_array_<master>_<task>.log

set -euo pipefail

LIB="${BUSCO_LIB:-$(dirname "$(readlink -f "$0")")/lib.sh}"
# shellcheck source=lib.sh
. "$LIB"

export https_proxy=${https_proxy:-$BUSCO_PROXY}
export http_proxy=${http_proxy:-$https_proxy}

if [ -z "${SLURM_ARRAY_TASK_ID:-}" ]; then
    echo "ERROR: SLURM_ARRAY_TASK_ID unset - this job must run as a task of a" >&2
    echo "       SLURM array (submit.sh scripts/run_busco_array.sbatch auto-computes --array)." >&2
    exit 1
fi

TASK=$(printf '%02d' "$SLURM_ARRAY_TASK_ID")
CHUNK=$BUSCO_CHUNKS/chunk_$TASK
OUT=$BUSCO_RESULTS/chunk_$TASK
FAILED=$OUT/failed_genomes.txt

if [ ! -d "$CHUNK" ]; then
    echo "ERROR: chunk dir missing: $CHUNK" >&2
    echo "       stage + chunk first (see header) or fix --array range" >&2
    exit 1
fi

mkdir -p "$OUT"

echo "=== chunk: $CHUNK ==="
ls -1 "$CHUNK"

if [ -z "$BUSCO_LINEAGE" ]; then
    # Auto-pick the best eukaryote lineage per genome.
    # BUSCO caches after the first download.
    LINEAGE_ARGS=(--auto-lineage-euk)
    MODE=autolineage-euk
else
    # Explicit lineage (passed to "busco -l"
    LINEAGE_ARGS=(-l "$BUSCO_LINEAGE")
    MODE="explicit:$BUSCO_LINEAGE"
fi
echo "=== mode=$MODE ==="

for f in "$CHUNK"/*.fa; do
    base=$(basename "$f")
    if find "$OUT" -maxdepth 4 -name "short_summary.specific.*${base}.txt" | grep -q .; then
        echo "SKIP $base (results exist)"
        continue
    fi
    echo "=== RUN $base $(date '+%F %T') ==="
    if ! apptainer exec --bind /work:/work "$BUSCO_SIF" busco \
            -i "$f" \
            "${LINEAGE_ARGS[@]}" \
            -m proteins \
            -c "$BUSCO_CPUS" \
            -o "$base" \
            --out_path "$OUT" \
            --download_path "$BUSCO_DOWNLOADS" \
            --opt-out-run-stats; then
        echo "FAIL $base $(date '+%F %T')" >> "$FAILED"
        echo "recorded failure: $base"
        continue
    fi
done

echo "=== failures ==="
cat "$FAILED" 2>/dev/null || echo "(none)"
echo "=== per-genome short summaries ==="
find "$OUT" -name "short_summary.specific.*" -exec grep -H "^# BUSCO was run" {} \; 2>/dev/null || true
