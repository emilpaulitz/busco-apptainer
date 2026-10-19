"""Contract tests for scripts/lib.sh (per-user configuration, ticket 006).

lib.sh must be safely sourceable from any script body and derive every path
from BUSCO_WORK (default: /work/<invoking-user>/busco). Environment variables
always win over the defaults. No user names may appear in the file itself.
"""

import os
import pwd
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "scripts" / "lib.sh"

VARS = [
    "BUSCO_WORK",
    "BUSCO_SIF",
    "BUSCO_DOWNLOADS",
    "BUSCO_RESULTS",
    "BUSCO_CHUNKS",
    "BUSCO_LOGS",
    "BUSCO_SEQ",
    "BUSCO_INPUT_DIR",
    "BUSCO_PROXY",
    "BUSCO_REPO_ROOT",
    "BUSCO_CPUS",
    "BUSCO_LINEAGE",
    "BUSCO_PARTITION",
    "BUSCO_ARRAY_LIMIT",
]

_SNIPPET = '. "$1" && for v in ' + " ".join(VARS) + '; do printf "%s=%s\\n" "$v" "${!v}"; done'


def source_lib(env_extra=None):
    env = dict(os.environ)
    for var in VARS:
        env.pop(var, None)  # isolate from any ambient config
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        ["bash", "-c", _SNIPPET, "libsh", str(LIB)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, f"sourcing lib.sh failed:\n{result.stderr}"
    out = {}
    for line in result.stdout.splitlines():
        key, _, value = line.partition("=")
        out[key] = value
    return out


def test_lib_exists():
    assert LIB.is_file(), f"missing {LIB}"


def test_defaults_derived_from_invoking_user():
    user = pwd.getpwuid(os.getuid()).pw_name
    work = f"/work/{user}/busco"
    got = source_lib()
    assert got["BUSCO_WORK"] == work
    assert got["BUSCO_SIF"] == f"{work}/busco_6.1.0.sif"
    assert got["BUSCO_DOWNLOADS"] == f"{work}/downloads"
    assert got["BUSCO_RESULTS"] == f"{work}/results"
    assert got["BUSCO_CHUNKS"] == f"{work}/chunks"
    assert got["BUSCO_LOGS"] == f"{work}/logs"
    assert got["BUSCO_SEQ"] == f"{work}/all_seqs"


def test_group_input_dir_default():
    got = source_lib()
    assert got["BUSCO_INPUT_DIR"] == (
        "/home/group/agnikoloski/genomes_for_arne/seqs_conform"
    )


def test_knob_defaults():
    got = source_lib()
    # ticket 012: 8 (was 16) - measured ~7 busy cpus per task
    assert got["BUSCO_CPUS"] == "8"
    # ticket 011: empty lineage default -> jobs run --auto-lineage-euk;
    # setting BUSCO_LINEAGE selects an explicit lineage instead. There is no
    # BUSCO_MODE knob anymore.
    assert got["BUSCO_LINEAGE"] == ""
    assert got["BUSCO_PARTITION"] == "all"
    assert got["BUSCO_ARRAY_LIMIT"] == ""
    assert got["BUSCO_PROXY"] == "http://proxy2.uni-potsdam.de:3128"


def test_repo_root_points_at_repo():
    got = source_lib()
    assert Path(got["BUSCO_REPO_ROOT"]).resolve() == REPO.resolve()


def test_env_overrides_win():
    got = source_lib(
        {
            "BUSCO_WORK": "/tmp/fakebusco",
            "BUSCO_CPUS": "32",
            "BUSCO_LINEAGE": "bacteria_odb12",
            "BUSCO_PARTITION": "gpu",
            "BUSCO_ARRAY_LIMIT": "4",
        }
    )
    assert got["BUSCO_WORK"] == "/tmp/fakebusco"
    assert got["BUSCO_SIF"] == "/tmp/fakebusco/busco_6.1.0.sif"
    assert got["BUSCO_DOWNLOADS"] == "/tmp/fakebusco/downloads"
    assert got["BUSCO_RESULTS"] == "/tmp/fakebusco/results"
    assert got["BUSCO_CHUNKS"] == "/tmp/fakebusco/chunks"
    assert got["BUSCO_LOGS"] == "/tmp/fakebusco/logs"
    assert got["BUSCO_SEQ"] == "/tmp/fakebusco/all_seqs"
    assert got["BUSCO_CPUS"] == "32"
    assert got["BUSCO_LINEAGE"] == "bacteria_odb12"
    assert got["BUSCO_PARTITION"] == "gpu"
    assert got["BUSCO_ARRAY_LIMIT"] == "4"


def test_no_hardcoded_user_in_lib():
    text = LIB.read_text()
    assert "/work/neumann19" not in text
    assert "/home/neumann19" not in text
