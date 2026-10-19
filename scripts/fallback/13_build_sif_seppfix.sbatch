#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --job-name=sif_seppfix
#SBATCH --chdir=/work/neumann19/busco/sepp_fix
#SBATCH --output=/work/neumann19/busco/logs/sif_seppfix_%j.log
#
# 13 - Rebuild the SIF with the sepp 4.5.6 seppJsonMerger.jar (ticket 003,
# phase 3). Builds the zero-network patch layer scripts/busco_seppfix.def
# (localimage on top of the existing SIF) because compute nodes currently
# have no outbound network; the canonical busco.def stays as the full
# recipe for environments where egress works. mksquashfs needs the
# batch-job memory allocation (2 GB ulimit on interactive nodes).

set -euo pipefail
module purge 2>/dev/null || true

# Egress only via proxy (AGENTS.md); harmless for the zero-network localimage
# build but required by any docker:// bootstrap or %post download.
export https_proxy=${https_proxy:-$BUSCO_PROXY}
export http_proxy=$https_proxy

FIX=/work/neumann19/busco/sepp_fix
DEF=$FIX/scripts/busco_seppfix.def
SIF=/work/neumann19/busco/busco_6.1.0.sif
TMP_SIF=$(mktemp --suffix=.sif /tmp/busco_build.XXXXXX)
trap 'rm -f "$TMP_SIF"' EXIT

apptainer build --force --fakeroot "$TMP_SIF" "$DEF"
rm -f "$SIF"
mv "$TMP_SIF" "$SIF"

echo "BUILD_SCRIPT_EXIT=$?"
apptainer exec "$SIF" java -jar /usr/local/bin/seppJsonMerger.jar 2>&1 | head -3 || true
