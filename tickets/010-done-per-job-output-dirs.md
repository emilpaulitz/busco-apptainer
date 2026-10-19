# 010 - Drop BUSCO_FORCE: per-job output dirs for the single runner

## Problem
Rerunning the same input needs `BUSCO_FORCE=1` because `-o` derives from the
input basename and BUSCO refuses existing run dirs (BuscoConfig.py:889).
`-f` is a plain `shutil.rmtree` of old results (BuscoConfig.py:953) - a failed
replacement run destroys hours of work. Failed runs leave their dir behind
(run_BUSCO.py:105-138), so retries hit refuse-overwrite anyway.

## Decision (user, 2026-09-09)
Per-job output dirs (`$BUSCO_RESULTS/single/job_$SLURM_JOB_ID`) for
run_busco.sbatch; `BUSCO_FORCE` knob removed. Deliberate re-runs = resubmit
(new job id -> fresh dir, old results preserved). mv-aside guard for the
requeue edge (same job id rerun): existing dir -> `.bak_<ts>`, never deleted.
Array runner unchanged (stable chunk dirs are its resume contract) - the
partial-dir gap there is a separate future ticket.

## Phases (each: pytest green + own commit)
1. RED: test_run_busco_sbatch.py - no BUSCO_FORCE/-f anywhere; OUT uses
   job_$SLURM_JOB_ID; mv-aside guard present, no rm -rf in active lines.
2. GREEN: run_busco.sbatch edits + header comment.
3. README: drop both BUSCO_FORCE mentions, document new results layout.
4. Rename ticket, final commit.

## Status: DONE

## Results (2026-09-09)
- RED/GREEN committed; 69 tests green (3 new contracts: no BUSCO_FORCE/-f,
  per-job OUT dir, mv-aside guard, no `rm -rf` in active lines).
- `run_busco.sbatch`: `OUT=$BUSCO_RESULTS/single/job_${SLURM_JOB_ID:-0}`;
  existing `$OUT/$BASE` moved to `.bak_<ts>` before the run (requeue edge);
  force knob deleted. `collect_results.py` needs no change (rglob already
  walks any depth; job dir becomes the TSV's first path component).
- README: rerun note + results/ layout updated.

## Hurdles
1. First draft of the no-`-f` regex matched legitimate uses (`readlink -f`,
   `[ ! -f "$INPUT" ]`); tightened to the actual injection point
   (`set -- ... -f`) + absence of the `BUSCO_FORCE` string anywhere.
