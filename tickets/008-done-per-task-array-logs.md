# 008 - Per-task SLURM logs for array jobs

## Problem

`submit.sh` injected `--output=$BUSCO_LOGS/%x_%j.log` for every job. For
`run_busco_array.sbatch` there is no `%a` in that pattern, so all array
tasks of one array job (e.g. 1866847_0.._10) wrote into the SAME file -
output of 11 concurrent chunk runs interleaved, effectively unreadable.
The user also guessed the filename wrong (`busco_<id>.log` instead of
`busco_array_<id>.log`), which hid the problem.

## Fix (RED/GREEN)

- RED `tests/test_submit_validation.py`: array submission must inject
  `--output=$BUSCO_LOGS/%x_%A_%a.log` (also with user-passed `--array=...`);
  single jobs keep `%x_%j.log` and must stay `%a`-free (in a non-array job
  `%a` expands to SLURM's 4294967294 sentinel).
- GREEN `scripts/submit.sh`: `OUT_PATTERN` selected per job type before
  `INJECT` is built; `run_busco_array.sbatch` gets `%x_%A_%a.log`
  (`%A` = array master jobid, `%a` = task id).
- Header comments updated: `submit.sh` (injected options) and
  `run_busco_array.sbatch` (per-task log poll hint).

## Hurdles

1. First GREEN attempt appended a second `--output` via `EXTRA`; sbatch
   would take the later one, but the tests (correctly) assert on all
   `--output=` occurrences and caught the duplicate. Refactored to pick
   `OUT_PATTERN` before `INJECT` - one option, no override subtlety.
2. An edit accidentally dropped the `--cpus-per-task` mention from the
   `submit.sh` header; caught by re-reading the diff and restored.

## Notes

- `%a` is unpadded, so per-task logs sort `_0, _1, _10, _2...` - cosmetic,
  SLURM patterns cannot zero-pad; intentionally NOT documented in README.
- Existing live logs of job 1866847 remain shared/interleaved; only new
  submissions get per-task files.
