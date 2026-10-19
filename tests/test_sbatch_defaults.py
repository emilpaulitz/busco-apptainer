"""#SBATCH header defaults must match the measured resource profile (ticket 012).

sacct for batch 1867567 (11 array tasks, real BUSCO work): MaxRSS 2.5-3.3G
vs --mem=32G (~10% used), ~7 of 16 allocated cpus busy (TotalCPU vs
Elapsed x AllocCPUS), longest task 3:56 vs --time=24:00:00. New defaults:
8 cpus, 8G mem, 2h for the array. Single jobs keep 12h (slowest observed
single run: 38 min, autolineage Capsicum, ticket 007) and also drop to
8 cpus / 8G.

BUSCO_CPUS (busco -c) and --cpus-per-task must stay consistent: the header
default covers plain submissions (submit.sh injects --cpus-per-task only
when BUSCO_CPUS is set in the environment).
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _directives(name):
    return [
        line.strip()
        for line in (REPO / name).read_text().splitlines()
        if line.startswith("#SBATCH")
    ]


def _one(name, key):
    hits = [d for d in _directives(name) if d.startswith(f"#SBATCH --{key}=")]
    assert len(hits) == 1, f"{name}: expected exactly one --{key}, got {hits}"
    return hits[0].split("=", 1)[1]


def test_array_header_defaults():
    assert _one("scripts/run_busco_array.sbatch", "cpus-per-task") == "8"
    assert _one("scripts/run_busco_array.sbatch", "mem") == "8G"
    # longest observed array task: 3:56 -> 2h is ~30x headroom
    assert _one("scripts/run_busco_array.sbatch", "time") == "02:00:00"


def test_single_header_defaults():
    assert _one("scripts/run_busco.sbatch", "cpus-per-task") == "8"
    assert _one("scripts/run_busco.sbatch", "mem") == "8G"
    # slower observed single run: 38 min (autolineage Capsicum, ticket 007)
    # -> 12h kept deliberately; cutting it risks TIMEOUT on bigger genomes
    assert _one("scripts/run_busco.sbatch", "time") == "12:00:00"
