# 011 - done: lineage-driven mode (`--auto-lineage-euk` default), drop BUSCO_MODE

## Request

Colleague: default to `--auto-lineage-euk` instead of `--auto-lineage` when
`BUSCO_LINEAGE` is not set. Decision: drop the `BUSCO_MODE` knob entirely -
behavior driven purely by `BUSCO_LINEAGE` (single job AND array):

- `BUSCO_LINEAGE` set -> `-l $BUSCO_LINEAGE` (array keeps `--offline`)
- `BUSCO_LINEAGE` unset -> `--auto-lineage-euk`

## Design notes

- lib.sh stopped defaulting `BUSCO_LINEAGE=eukaryota_odb12.2` (otherwise it
  is never unset); new default "".
- Array runner DROPS `--offline` in autolineage mode: auto-lineage resolves
  the final lineage per genome at runtime via a cascade; the needed datasets
  cannot all be pre-seeded, `--offline` would fail on any not-yet-cached one
  (ticket 007 trap, generalized).
- The array script previously exported NO proxy (it only survived via
  --offline); it now has the same unconditional proxy export as
  run_busco.sbatch (AGENTS.md).
- Trade-off: a first autolineage array may download cascade datasets
  concurrently through the proxy (the phone-home storm `--offline` avoided).
  Mitigation: BUSCO caches after first download; per-genome resume-safety
  makes an affected task cheaply resubmittable. Documented in README.

## Hurdles

- The functional stub test caught a leftover `--offline` in the array busco
  invocation after `-l "$BUSCO_LINEAGE"` had been replaced by
  `"${LINEAGE_ARGS[@]}"` - a plain content test would have missed it
  (RED->GREEN loop paid off).
- `test_no_busco_mode_knob` flagged the run_busco.sbatch header comment;
  fixed by rewriting the knob documentation.
- Avoided `${LINEAGE_ARGS[@]}` expansion problems under `set -u` by having
  both branches assign a non-empty array before use.

## Status

- [x] RED: test_lib_sh (lineage default "", no BUSCO_MODE),
      test_run_busco_sbatch (branch on -z BUSCO_LINEAGE),
      new test_run_busco_array_sbatch (stub apptainer, both modes),
      test_submit_validation (drop BUSCO_MODE from env pop list) (30a4bff)
- [x] GREEN: lib.sh, run_busco.sbatch, run_busco_array.sbatch, README
      (75 tests pass, 69 baseline + 6 new contracts)
