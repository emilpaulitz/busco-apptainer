"""submit.sh must validate the run_busco.sbatch input BEFORE sbatch (ticket 007).

The README placeholder "MY.fa" was submitted literally; the batch job failed
in 1 s and the error only surfaced in logs/busco_<id>.log. A nonexistent or
missing input must instead fail at submission time on the login node - without
calling sbatch at all.

sbatch is stubbed via PATH: the stub appends its argv to a log file, so tests
can assert whether a submission actually happened.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SUBMIT = REPO / "scripts" / "submit.sh"


@pytest.fixture()
def stub_env(tmp_path):
    """Env with BUSCO_WORK in tmp and a stub sbatch recording its argv."""
    work = tmp_path / "busco"
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub_log = tmp_path / "sbatch_calls.log"
    stub = stub_dir / "sbatch"
    stub.write_text(f"#!/bin/bash\nprintf '%s\\n' \"$@\" >> {stub_log}\n")
    stub.chmod(0o755)
    env = dict(os.environ)
    for var in (
        "BUSCO_WORK", "BUSCO_SIF", "BUSCO_DOWNLOADS", "BUSCO_RESULTS",
        "BUSCO_CHUNKS", "BUSCO_LOGS", "BUSCO_SEQ", "BUSCO_INPUT_DIR",
        "BUSCO_REPO_ROOT", "BUSCO_CPUS", "BUSCO_LINEAGE",
        "BUSCO_PARTITION", "BUSCO_ARRAY_LIMIT",
    ):
        env.pop(var, None)
    env["PATH"] = f"{stub_dir}:{env['PATH']}"
    env["BUSCO_WORK"] = str(work)
    return {"env": env, "work": work, "log": stub_log}


def _run(stub_env, *args):
    return subprocess.run(
        [str(SUBMIT), *args],
        capture_output=True,
        text=True,
        env=stub_env["env"],
        timeout=60,
    )


def _submitted(stub_env):
    return stub_env["log"].exists() and stub_env["log"].read_text() != ""


def test_nonexistent_input_fails_at_submission(stub_env):
    r = _run(stub_env, "scripts/run_busco.sbatch", "/nonexistent/MY.fa")
    assert r.returncode != 0
    assert "not found" in r.stderr
    assert "MY.fa" in r.stderr
    assert "ls " in r.stderr  # hint where staged inputs live
    assert not _submitted(stub_env), "sbatch must not be called for a bad path"


def test_missing_input_arg_fails_at_submission(stub_env):
    r = _run(stub_env, "scripts/run_busco.sbatch")
    assert r.returncode != 0
    assert "input" in r.stderr
    assert not _submitted(stub_env)


def test_relative_input_fails_at_submission(stub_env):
    # The job runs with --chdir=$BUSCO_WORK, so a relative input would
    # resolve differently on the compute node.
    (stub_env["work"] / "all_seqs").mkdir(parents=True)
    (stub_env["work"] / "all_seqs" / "G.fa").touch()
    r = _run(stub_env, "scripts/run_busco.sbatch", "all_seqs/G.fa")
    assert r.returncode != 0
    assert "absolute" in r.stderr
    assert not _submitted(stub_env)


def test_existing_fa_is_submitted(stub_env):
    fa = stub_env["work"] / "all_seqs" / "G.fa"
    fa.parent.mkdir(parents=True)
    fa.touch()
    r = _run(stub_env, "scripts/run_busco.sbatch", str(fa))
    assert r.returncode == 0, r.stderr
    assert _submitted(stub_env)
    calls = stub_env["log"].read_text()
    assert str(fa) in calls
    assert str(stub_env["work"] / "build" / "run_busco.sbatch") in calls


def test_non_fa_suffix_warns_but_submits(stub_env):
    # sepp munges the literal string "fasta" in paths (BUSCO #432/#781);
    # .fa is the supported suffix - warn loudly, do not silently submit.
    fasta = stub_env["work"] / "all_seqs" / "G.fasta"
    fasta.parent.mkdir(parents=True)
    fasta.touch()
    r = _run(stub_env, "scripts/run_busco.sbatch", str(fasta))
    assert r.returncode == 0, r.stderr
    assert "WARNING" in r.stderr
    assert _submitted(stub_env)


def test_other_jobs_still_submit_without_args(stub_env):
    r = _run(stub_env, "scripts/build_sif.sbatch")
    assert r.returncode == 0, r.stderr
    assert _submitted(stub_env)


def _output_options(stub_env):
    return [
        line
        for line in stub_env["log"].read_text().splitlines()
        if line.startswith("--output=")
    ]


def test_array_job_gets_per_task_log_pattern(stub_env):
    # Without %a all array tasks share ONE %x_%j.log, interleaving the
    # output of the concurrent chunk runs (seen live, ticket 008).
    # %A = array master jobid, %a = task id -> one log per task.
    (stub_env["work"] / "chunks" / "chunk_00").mkdir(parents=True)
    r = _run(stub_env, "scripts/run_busco_array.sbatch")
    assert r.returncode == 0, r.stderr
    assert _output_options(stub_env) == [
        f"--output={stub_env['work']}/logs/%x_%A_%a.log"
    ]


def test_explicit_array_option_still_gets_per_task_logs(stub_env):
    (stub_env["work"] / "chunks" / "chunk_00").mkdir(parents=True)
    r = _run(stub_env, "scripts/run_busco_array.sbatch", "--array=0-3")
    assert r.returncode == 0, r.stderr
    assert _output_options(stub_env) == [
        f"--output={stub_env['work']}/logs/%x_%A_%a.log"
    ]
    assert "--array=0-3" in stub_env["log"].read_text().splitlines()


def test_single_job_log_pattern_has_no_array_placeholders(stub_env):
    # In a non-array job %a would expand to SLURM's 4294967294 sentinel,
    # so the %x_%j.log pattern must stay %a-free.
    fa = stub_env["work"] / "all_seqs" / "G.fa"
    fa.parent.mkdir(parents=True)
    fa.touch()
    r = _run(stub_env, "scripts/run_busco.sbatch", str(fa))
    assert r.returncode == 0, r.stderr
    assert _output_options(stub_env) == [
        f"--output={stub_env['work']}/logs/%x_%j.log"
    ]


def test_array_job_without_chunks_dir_fails_loudly(stub_env):
    # ticket 014: chunks/ missing -> find failed under set -euo pipefail,
    # the $(... | wc -l) assignment killed submit.sh SILENTLY before the
    # warning and before sbatch. Must instead hard-fail with guidance.
    r = _run(stub_env, "scripts/run_busco_array.sbatch")
    assert r.returncode != 0
    assert "chunk" in r.stderr
    assert "make_chunks" in r.stderr
    assert not _submitted(stub_env), "sbatch must not be called without chunks"


def test_array_job_with_empty_chunks_dir_fails_loudly(stub_env):
    # Same trap with chunks/ present but no chunk_* dirs: a plain submission
    # (no --array) would die on the node with SLURM_ARRAY_TASK_ID unset.
    (stub_env["work"] / "chunks").mkdir(parents=True)
    r = _run(stub_env, "scripts/run_busco_array.sbatch")
    assert r.returncode != 0
    assert "chunk" in r.stderr
    assert "make_chunks" in r.stderr
    assert not _submitted(stub_env)
