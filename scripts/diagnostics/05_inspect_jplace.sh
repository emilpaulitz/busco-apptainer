#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --job-name=inspect_jplace
#SBATCH --chdir=/work/neumann19/busco
#SBATCH --output=/work/neumann19/busco/inspect_%j.log
#
# Inspect the .jplace files + Java merger to pinpoint the NumberFormatException.
# Runs in a batch job so no progress bars/escape sequences reach the terminal.

set -euo pipefail
SIF=/work/neumann19/busco/busco_6.1.0.sif

# 1. Find all .jplace files from the last run
find /work/neumann19/busco/test_odb12 -name "*.jplace" > /work/neumann19/busco/work/jplace_list.txt 2>/dev/null || true

# 2. Dump JSON structure of a sample
SAMPLE=$(head -1 /work/neumann19/busco/work/jplace_list.txt 2>/dev/null || true)
if [ -n "$SAMPLE" ]; then
    python3 - "$SAMPLE" <<'EOF' > /work/neumann19/busco/work/jplace_sample.txt 2>&1
import json,sys
p=json.load(open(sys.argv[1]))
print("keys:", list(p.keys()))
pl=p.get('placements',[])
print("n_placements:", len(pl))
bad=0
for i,plc in enumerate(pl[:20]):
    for att in plc.get('p',[]):
        # find null / non-numeric entries
        for v in att:
            if v is None:
                bad+=1
                print(f"NULL in placement {i}: {att}")
    print(f"plc[{i}]:", {k:(plc[k] if k!='nm' else plc[k][:2]) for k in ('p','n','nm') if plc.get(k) is not None})
print("bad nulls total:", bad)
EOF
fi
cat /work/neumann19/busco/work/jplace_sample.txt
echo "DONE"