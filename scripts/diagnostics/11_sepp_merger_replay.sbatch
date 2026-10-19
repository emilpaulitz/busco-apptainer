#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --job-name=sepp_merger
#SBATCH --chdir=/work/neumann19/busco/sepp_fix
#SBATCH --output=/work/neumann19/busco/logs/sepp_merger_%j.log
#
# 11 - Isolated seppJsonMerger replay (ticket 003). Feeds the reconstructed
# stdin streams (scripts/10) from the preserved failing run into the merger.
#   mode=old: bundled 4.5.5 jar in the SIF -> expect NumberFormatException
#             on every stream (RED, reproduces run_odb12_1866053.log:264).
#   mode=new: sepp 4.5.6 jar on /work -> expect valid merged JSON (GREEN).

set -uo pipefail

SIF=/work/neumann19/busco/busco_6.1.0.sif
FIX=/work/neumann19/busco/sepp_fix
MODE=${1:-old}
TARBALL_SHA256=e4aae4908b33d54d34c8796bc1f5aed38e8969c411102d713da075a0d7832560

case "$MODE" in
  old)
    JAR=/usr/local/bin/seppJsonMerger.jar
    OUTDIR=$FIX/old_out
    ;;
  new)
    # NOTE: compute nodes cannot reach github; the jar is pre-staged on the
    # login node from the sha256-verified v4.5.6 tarball.
    JAR=$FIX/jars/seppJsonMerger-4.5.6.jar
    if [ ! -f "$JAR" ]; then
      echo "missing $JAR - stage it from the verified tarball first" >&2
      exit 2
    fi
    OUTDIR=$FIX/new_out
    ;;
  *)
    echo "usage: sbatch $0 old|new" >&2; exit 2 ;;
esac

mkdir -p "$OUTDIR"
FAIL=0
while IFS=$'\t' read -r STREAM JPLACE NPL; do
  NAME=$(basename "$STREAM" .stream)
  if apptainer exec --bind /work:/work "$SIF" \
      java -jar "$JAR" - - "$OUTDIR/$NAME.json" < "$STREAM" \
      > "$OUTDIR/$NAME.stdout" 2> "$OUTDIR/$NAME.stderr"; then
    echo "OK   $NAME"
  else
    echo "FAIL $NAME: $(tail -1 "$OUTDIR/$NAME.stderr")"
    FAIL=$((FAIL + 1))
  fi
done < "$FIX/streams/manifest.tsv"

echo "SUMMARY mode=$MODE failed=$FAIL total=$(wc -l < "$FIX/streams/manifest.tsv")"
if [ "$MODE" = old ] && [ "$FAIL" -gt 0 ]; then
  echo "RED confirmed: old jar fails as expected"
  exit 0
fi
if [ "$MODE" = new ] && [ "$FAIL" -eq 0 ]; then
  echo "GREEN confirmed: new jar succeeds on all streams"
  exit 0
fi
exit 1
