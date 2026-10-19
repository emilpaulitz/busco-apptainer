"""Contracts for scripts/run_busco_array.sbatch (ticket 011).

Lineage-driven mode, no BUSCO_MODE knob:
- BUSCO_LINEAGE set -> explicit `-l $BUSCO_LINEAGE` (exactly one
  dataset; downloads on demand like autolineage, ticket 013).
- BUSCO_LINEAGE unset -> `--auto-lineage-euk`: the final lineage is
  only known at runtime (cascade per genome), so any not-yet-cached
  dataset must be downloadable (ticket 007 trap). Neither mode may use
  `--offline` (ticket 013): it hard-fails on any not-yet-cached dataset
  ("Unable to run BUSCO in offline mode"). Both need the proxy export
  (compute nodes have no direct egress, AGENTS.md)
  - the array script had none before ticket 011.

apptainer is stubbed via PATH: the stub records its argv, so the tests
assert the exact busco invocation per mode without running BUSCO.
"""

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_busco_array.sbatch"
LIB = REPO / "scripts" / "lib.sh"

ENV_VARS = (
    "BUSCO_LIB", "BUSCO_WORK", "BUSCO_SIF", "BUSCO_DOWNLOADS",
    "BUSCO_RESULTS", "BUSCO_CHUNKS", "BUSCO_LOGS", "BUSCO_SEQ",
    "BUSCO_INPUT_DIR", "BUSCO_REPO_ROOT", "BUSCO_CPUS",
    "BUSCO_LINEAGE", "BUSCO_MODE", "BUSCO_PARTITION", "BUSCO_ARRAY_LIMIT",
)


def _make_env(tmp_path, extra=None):
    work = tmp_path / "work"
    chunk = work / "chunks" / "chunk_00"
    chunk.mkdir(parents=True)
    (chunk / "G.fa").write_text(">G\nMKV\n")
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub_log = tmp_path / "apptainer_calls.log"
    stub = stub_dir / "apptainer"
    stub.write_text(f"#!/bin/bash\nprintf '%s\\n' \"$@\" >> {stub_log}\nexit 0\n")
    stub.chmod(0o755)
    env = dict(os.environ)
    for var in ENV_VARS:
        env.pop(var, None)
    env["PATH"] = f"{stub_dir}:{env['PATH']}"
    env["BUSCO_LIB"] = str(LIB)
    env["BUSCO_WORK"] = str(work)
    env["SLURM_ARRAY_TASK_ID"] = "0"
    if extra:
        env.update(extra)
    return {"env": env, "work": work, "log": stub_log}


def _run(envd):
    return subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env=envd["env"],
        timeout=60,
    )


def _busco_argv(envd):
    """Args of the (single) apptainer call after the 'busco' word."""
    lines = envd["log"].read_text().splitlines()
    return lines[lines.index("busco") + 1 :]


def test_lineage_unset_runs_autolineage_euk_without_offline(tmp_path):
    envd = _make_env(tmp_path)  # no BUSCO_LINEAGE -> lib.sh default ""
    r = _run(envd)
    assert r.returncode == 0, r.stderr
    argv = _busco_argv(envd)
    assert "--auto-lineage-euk" in argv
    assert "-l" not in argv
    assert "--offline" not in argv, (
        "autolineage must be able to download cascade datasets on demand"
    )


def test_lineage_set_uses_explicit_flag_without_offline(tmp_path):
    envd = _make_env(tmp_path, {"BUSCO_LINEAGE": "eukaryota_odb12.2"})
    r = _run(envd)
    assert r.returncode == 0, r.stderr
    argv = _busco_argv(envd)
    assert "--auto-lineage-euk" not in argv
    i = argv.index("-l")
    assert argv[i + 1] == "eukaryota_odb12.2"
    assert "--offline" not in argv, (
        "explicit mode must download on demand like autolineage (ticket 013)"
    )


def test_proxy_export_is_unconditional():
    # Both modes share this export; either may download a missing dataset
    # (ticket 013) and compute nodes only reach the internet via the
    # proxy (AGENTS.md). The export must sit before the lineage branch.
    text = SCRIPT.read_text()
    assert "export https_proxy=${https_proxy:-$BUSCO_PROXY}" in text
    export_pos = text.index("export https_proxy=")
    branch_pos = text.index('if [ -z "$BUSCO_LINEAGE" ]')
    assert export_pos < branch_pos


def test_no_busco_mode_knob():
    # ticket 011: the mode is fully determined by BUSCO_LINEAGE
    assert "BUSCO_MODE" not in SCRIPT.read_text()
