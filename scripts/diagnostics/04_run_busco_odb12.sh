#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --job-name=busco_odb12
#SBATCH --chdir=/work/neumann19/busco
#SBATCH --output=/work/neumann19/busco/run_odb12_%j.log
#
# 04 - Single-genome BUSCO test run with the odb12 dataset version instead
# of odb12.2. seppJsonMerger.jar fails with a NumberFormatException on
# odb12.2 (BUSCO issue #834); testing whether odb12 avoids it.

set -euo pipefail

SIF=/work/neumann19/busco/busco_6.1.0.sif
WORK=/work/neumann19/busco
RUN=$WORK/test_odb12
SEQDIR=$RUN/seqs
OUT=$RUN

rm -rf "$RUN"
mkdir -p "$SEQDIR"
cp "$WORK/test_green2/seqs/Capsicum_annuum_combined.fa" "$SEQDIR/Capsicum_annuum_combined.fa"

apptainer exec --bind /work:/work "$SIF" busco \
    -i "$SEQDIR" \
    --auto-lineage-euk \
    -m proteins \
    -c 16 \
    -o BUSCO_res \
    --out_path "$OUT" \
    --download_path "$WORK/downloads" \
    --datasets_version odb12 \
    --opt-out-run-stats

echo "BUSCO_EXIT=$?"