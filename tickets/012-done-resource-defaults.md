# 012 - done: cut array/single job resource defaults to measured profile

## Request

Check how much resources the array jobs actually need; reduce HPC usage.

## Evidence (sacct, batch 1867567, 11 tasks, real BUSCO work)

- MaxRSS 2.5-3.3G vs `--mem=32G` (~10% used)
- ~7 of 16 allocated cpus busy (TotalCPU vs Elapsed x AllocCPUS)
- longest task 3:56 vs `--time=24:00:00`
- earlier real batches (1866187/1866200) agree

No forced re-run was needed (and BUSCO_FORCE no longer exists, ticket 010):
the measurements come from the already-completed batch; future runs
re-measure via the new README sacct one-liner.

## Change (user: "cut mem + cpus + time", both headers + lib.sh, tested)

- `run_busco_array.sbatch`: `--cpus-per-task=16->8`, `--mem=32G->8G`,
  `--time=24:00:00->02:00:00`
- `run_busco.sbatch`: cpus 16->8, mem 32G->8G; time KEEPS 12:00:00
  (slowest observed single run: 38 min autolineage Capsicum, ticket 007;
  a cut risks TIMEOUT on bigger genomes)
- `lib.sh`: `BUSCO_CPUS` 16->8 (busco -c; consistent with the header
  default: submit.sh injects --cpus-per-task only when BUSCO_CPUS is set,
  so a plain submit runs header 8 + -c 8)
- README: config table, monitoring sacct one-liner, measured numbers +
  per-submission override hint for OOM/TIMEOUT cases
- `build_sif.sbatch` out of scope (mksquashfs needs memory, AGENTS.md)

## Hurdles

- `rg` was unavailable in the shell (exit 127); used the Grep tool instead.
- Single-job time limit: evidence covers only one slow genome (38 min), so
  12h kept and the reasoning is pinned in the test docstring, not guessed.

## Status

- [x] RED: tests/test_sbatch_defaults.py (header directives),
      test_lib_sh BUSCO_CPUS 8 (2ef3a23)
- [x] GREEN: headers, lib.sh, README (77 tests pass)
