#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --job-name=inspect_tree
#SBATCH --chdir=/work/neumann19/busco
#SBATCH --output=/work/neumann19/busco/inspect_tree_%j.log

set -euo pipefail

SAMPLE=$(find /work/neumann19/busco/test_odb12 -name "*.jplace" | head -1)
BASE_TREE=/work/neumann19/busco/downloads/placement_files/tree.eukaryota_odb12.2026-01-01.nwk
[ -f "$BASE_TREE" ] || BASE_TREE=$(ls /work/neumann19/busco/downloads/placement_files/tree.*.nwk | head -1)

python3 - "$SAMPLE" "$BASE_TREE" <<'EOF' > /work/neumann19/busco/work/tree_analysis.txt 2>&1
import json, sys, re
jf, basef = sys.argv[1], sys.argv[2]
j = json.load(open(jf))
print("jplace file:", jf)
print("fields:", j.get("fields"))
print("tree:", j.get("tree")[:200], "...")
print("version:", j.get("version"))
print("n_placements:", len(j.get("placements", [])))
for i, plc in enumerate(j.get("placements", [])[:3]):
    print(f"plc[{i}] p:", plc.get("p"))
print()
base = open(basef).read()
print("base tree len:", len(base))
print("base tree head:", base[:200])
# check if any placement edge_num exceeds what's in subset tree
EOF
cat /work/neumann19/busco/work/tree_analysis.txt