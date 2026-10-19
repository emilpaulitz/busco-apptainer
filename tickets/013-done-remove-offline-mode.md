# 013 - done: remove --offline everywhere

## Request

User: "I'd like to get rid of it completely."

## Evidence (BUSCO 6.1.0; SIF == GitHub source, diffed byte-identical)

- Without --offline every invocation fetches file_versions.tsv at startup
  (BuscoDownloadManager.py:51). A 429/proxy failure is fatal *per genome
  invocation* -> recorded in failed_genomes.txt, resubmit-safe.
- Cached-but-stale dataset: auto-updated in place, old version retained as
  `<dataset>.old` (BuscoDownloadManager.py:294). Logged twice at WARNING
  (:278, :258) -> post-run check: `grep -r "updated automatically"
  $BUSCO_RESULTS $BUSCO_LOGS`.
- Per-run log reliably lands in `$OUT/<base>/logs/busco.log` via
  move_log_file in a finally (BuscoRunner.py:1116, run_BUSCO.py:152) - also
  for failed genomes. Verified against real /work results layout.

## Change

- run_busco_array.sbatch: explicit branch = `-l $BUSCO_LINEAGE` only;
  explicit mode downloads on demand like autolineage. Pre-cache now
  optional (still recommended to avoid a first-use download stampede).
- Comment sync: array header/proxy/explicit branch, lib.sh BUSCO_LINEAGE,
  run_busco.sbatch proxy note, both test docstrings.

## Hurdles

- BuscoLogger.py:187 first writes `busco_<pid>.log` in the job CWD, NOT
  `logs/busco.log`; the final name/location only comes from move_log_file.
- The Grep tool showed a no-op edit of mine ate a newline in
  run_busco_array.sbatch (comment merged with LINEAGE_ARGS line); caught
  by re-reading and fixed before commit.
- Not end-to-end tested: triggering a real stale-dataset auto-update needs
  network + the server shipping a newer dataset than the cache.
