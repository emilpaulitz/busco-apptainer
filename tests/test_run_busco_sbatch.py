"""Content contracts for scripts/run_busco.sbatch (tickets 007/010/011).

Ticket 011: lineage-driven mode, no BUSCO_MODE knob. BUSCO_LINEAGE unset ->
--auto-lineage-euk (auto-pick within eukaryotes); set -> explicit -l.

Explicit lineage mode must not use --offline: it silently requires a
pre-downloaded dataset ("Unable to run BUSCO in offline mode" on a fresh
/work dir) and was the confusion trap behind ticket 007. BUSCO downloads a
missing dataset itself when the proxy is set - so the proxy export must be
unconditional, not only in autolineage mode.

Ticket 010: reruns must never need BUSCO_FORCE/-f (BUSCO's -f is a plain
rmtree of the old run dir). Each submission writes to a per-job dir
(job_$SLURM_JOB_ID); an existing dir is moved aside, never deleted.

Ticket 013: --offline is gone everywhere; the array runner (tested in
test_run_busco_array_sbatch.py) no longer uses it in explicit mode either.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_busco.sbatch"


def _active_lines():
    return [l for l in SCRIPT.read_text().splitlines() if not l.lstrip().startswith("#")]


def test_no_offline_flag():
    assert not any("--offline" in l for l in _active_lines())


def test_proxy_export_is_unconditional():
    text = SCRIPT.read_text()
    assert "export https_proxy=${https_proxy:-$BUSCO_PROXY}" in text
    # after the export, no lineage branch may revoke it; the export must
    # sit before the branching, not inside the autolineage branch (ticket
    # 011: the branch is on empty $BUSCO_LINEAGE, not on BUSCO_MODE)
    export_pos = text.index("export https_proxy=")
    branch_pos = text.index('if [ -z "$BUSCO_LINEAGE" ]')
    assert export_pos < branch_pos


def test_lineage_unset_runs_autolineage_euk():
    # ticket 011: no BUSCO_LINEAGE set -> auto-pick within eukaryotes
    # (NOT full --auto-lineage, which would also consider prokaryote
    # datasets and can mis-select, ticket 005)
    text = SCRIPT.read_text()
    branch = text.index('if [ -z "$BUSCO_LINEAGE" ]')
    after = text[branch:]
    assert re.search(r'set -- --auto-lineage-euk(\s|$)', after), (
        "BUSCO_LINEAGE unset branch must run --auto-lineage-euk"
    )


def test_no_busco_mode_knob():
    # ticket 011: the mode is fully determined by BUSCO_LINEAGE
    assert "BUSCO_MODE" not in SCRIPT.read_text()


def test_lineage_set_uses_lineage_flag():
    text = SCRIPT.read_text()
    m = re.search(r'set -- -l "\$BUSCO_LINEAGE"(\s|$)', text)
    assert m, "explicit branch must select the lineage via -l $BUSCO_LINEAGE"


def test_no_busco_force_knob():
    # ticket 010: -f rmtree's the old results (BuscoConfig.py:953); reruns
    # must go to a fresh per-job dir instead of ever overwriting
    text = SCRIPT.read_text()
    assert "BUSCO_FORCE" not in text
    # force is injected via arg-building: 'set -- "$@" -f'
    assert not any(re.search(r'set --.*\s-f(\s|$)', l) for l in _active_lines())


def test_per_job_output_dir():
    # ticket 010: every submission -> own dir; re-runs never collide
    assert any(
        "OUT=$BUSCO_RESULTS/single/job_${SLURM_JOB_ID:-0}" in l
        for l in _active_lines()
    )


def test_existing_dir_moved_aside_never_deleted():
    # ticket 010: requeue edge (same job id) - relocate the old run dir
    # instead of letting BUSCO rmtree it; no rm -rf in active lines
    text = SCRIPT.read_text()
    assert re.search(r'mv .+\.bak_', text)
    assert "rm -rf" not in "\n".join(_active_lines())
