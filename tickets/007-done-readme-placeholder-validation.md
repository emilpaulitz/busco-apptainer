# 007 - README placeholder `MY.fa` submitted literally; failure invisible outside the log

## Problem
(unchanged, see above)

## Plan additions (decided 2026-09-09 with user)
6. Drop `--offline` from `run_busco.sbatch` explicit mode (user choice A):
   the flag silently requires a pre-downloaded dataset and was the second
   confusion trap. BUSCO downloads a missing lineage itself when the proxy
   is set; proxy export becomes unconditional. The array runner KEEPS
   `--offline` (88 concurrent phone-homes, ticket 002).
7. README smoke example: `Chloropicon_primus_combined.fa` (smallest genome
   with a strong result; Capsicum dropped from README entirely).

## Status: DONE

## Results (2026-09-09)
- RED/GREEN committed: `tests/test_run_busco_sbatch.py` (no functional
  `--offline`, unconditional proxy export, explicit keeps `-l
  $BUSCO_LINEAGE`) + `tests/test_submit_validation.py` (6 cases); 63 tests
  green.
- submit.sh now fails fast on the login node: nonexistent input, missing
  arg, relative path (job chdirs to $BUSCO_WORK), warns on non-`.fa`
  suffix (sepp #432/#781) - no sbatch call for bad input.
- README: real smoke genome + `ls $BUSCO_SEQ` hint + post-submit log/sacct
  verification note; `MY.fa` gone.
- Cluster acceptance:
  - Bonus: autolineage Capsicum (1866779, 38:47) COMPLETED,
    ACCEPTANCE PASSED, solanales, C:69.7% - ticket-006 exact match.
  - Smoke, user path verbatim (1866829): COMPLETED in 12 s,
    C:96.0%[S:95.2%,D:0.8%],F:0.8%,M:3.2%,n:125 - ticket-002 exact match.
  - `collect_results.py`: 2 rows, 0 EMPTY.

## Hurdles
1. Failure invisibility: a finished job vanishes from `squeue`; the error
   only lived in `logs/busco_<id>.log`. README now documents
   log + `sacct` checking after every submit.
2. "No results" had two stacked causes: the `MY.fa` placeholder AND a
   never-bootstrapped dataset dir - the old work dir had been archived to
   `/work/neumann19/busco_old_20260908/` (downloads + 88-genome TSVs moved
   with it; used to pick the smoke genome without burning cluster time).
3. The failed explicit attempt left an empty run dir, so the retry hit
   BUSCO's refuse-overwrite; needed the documented `BUSCO_FORCE=1`. With
   submit-time validation this can no longer happen for bad paths.
4. `--offline` in explicit mode: chosen in ticket 002 for the ARRAY (88
   concurrent phone-homes) but copied into the single runner where it
   silently requires a pre-downloaded dataset ("Unable to run BUSCO in
   offline mode"). Removed there; contract tests prevent regression.
