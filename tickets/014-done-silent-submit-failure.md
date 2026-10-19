# 014 - done: silent submit failure + unactionable stage output

## Observed (login node, ~17:39)

1. `make_chunks.py` run before staging -> raw FileNotFoundError traceback
   (user error, but no guidance back to the correct order).
2. `stage_genomes.py` (real copy, no --dry-run) printed "planned: 88 file(s)"
   - same wording as a dry run; no report path, no next-step hint. Staging
   actually SUCCEEDED (88 .fa in $BUSCO_SEQ, report written, 0 suspicious).
3. `submit.sh scripts/run_busco_array.sbatch` printed NOTHING, exited 1,
   submitted nothing (sacct: no job after 16:24; logs/ has no array log).

## Root cause (submit.sh:156)

    n=$(find "$BUSCO_CHUNKS" -maxdepth 1 -type d -name 'chunk_*' 2>/dev/null | wc -l)

under `set -euo pipefail`: chunks/ missing -> find fails (stderr already
/dev/null'd) -> pipefail makes the substitution return 1 -> the assignment
propagates that status -> `set -e` kills the script SILENTLY before the
intended WARNING (line 162) and before sbatch. Un-tested path: chunks/
existed for all earlier runs (arrays 1866847 / 1867567); it had been deleted
since. Reproduced with a bash -c one-liner (exit 1, zero output).

## Change

- submit.sh: chunk count is pipefail-proof (`[ -d ]` pre-check + `|| true`
  inside the braces). Missing/empty chunk dirs -> hard-fail WITHOUT sbatch
  (user decision; a plain submission would die on the node) and print the
  exact stage + make_chunks commands. Applies to explicit --array too.
- stage_genomes.py: real runs print `staged: N file(s) -> <dst>`, the report
  path and the next make_chunks command; `planned:` is dry-run-only.
- make_chunks.py: missing src dir -> argparse error with staging hint,
  no traceback.
- Tests: 4 new (2 submit, 1 stage CLI, 1 make_chunks CLI); 82 pass.
- End-to-end smoke with stubbed sbatch: silent case now errors loudly,
  stage -> chunk -> submit yields --array=0-N as before.

## Hurdles

- bash gotcha confirmed by experiment: `set -e` + `var=$(false_pipeline)`
  exits silently (no message, the failure is the command substitution's
  status) - the classic `cmd | wc -l` under pipefail trap. Note the
  sibling `[ -n "$X" ] && cmd` idiom is exempt (failure inside an AND-OR
  list, not the final command) - that is why line 159 never bit.
- First wording of the dry-run line broke my own test literal
  ("planned (dry run, ...): N" vs asserted "planned: N file(s)"); reordered
  to "planned: N file(s) (dry run, nothing copied)".
- The EMPTY-chunks-dir case (dir exists, no chunk_*) previously warned and
  submitted a doomed plain job; only the MISSING-dir case was silent. Both
  now hard-fail per the user's decision.
