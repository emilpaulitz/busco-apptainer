# 001 - Port BUSCO container from Docker to Apptainer on the HPC

## Goal
The repo builds BUSCO via Docker. The HPC (`n-hpc-ca2`, apptainer 1.2.5)
only offers Apptainer/Singularity, and I am a normal user with no sudo rights.
Produce a runnable BUSCO `.sif` and SLURM scripts to process 88 genomes.

## Approach
Bootstrap the SIF directly from the prebuilt biocontainer image
(`quay.io/biocontainers/busco:6.1.0--pyhdfd-78af_2`), mirroring the repo's
`Dockerfile` which does `FROM quay.io/biocontainers/busco:5.6.1--...`. This
avoids all conda/packaging work entirely.

## Status: IN PROGRESS

## Progress (commit history)
- `busco.def` + build script added, SIF built at /work/neumann19/busco/busco_6.1.0.sif (765M).
- `busco --version` -> 6.1.0 confirmed in the container.
- RED test (original `.fasta` name): fails in sepp at `hmmsearch` subproblem P_4
  (JobError, exit 1, "No error messages available").
- GREEN test (renamed `.fa`): still fails in sepp at `hmmsearch` subproblem P_10.
  - The `fasta -> jplace` mangled dirs are GONE after the rename, so the
    `.fa` workaround for sepp issues #432/#781 is valid.
  - Remaining failure: sepp-internal `hmmsearch` subprocess returns exit 1
    under sepp's 16-way concurrency, but the IDENTICAL command succeeds when
    run standalone with the container. Not OOM (503 GB RAM free). sepp logs
    are empty (sepp consumes child stdout/stderr).

## Hurdles
1. sepp `fasta -> jplace` path bug (BUSCO issues #432, #781). Workaround:
   ensure no input filename / run path contains the literal string "fasta"
   (rename `.fasta` -> `.fa`). Constructed:
   the colleague's original error
   `.../Capsicum_annuum_combined.jplace/.../root/P_11` was this bug.
2. sepp-internal `hmmsearch` failing exit-1 under concurrency (BUSCO issue #432
   also mentions sepp hmmsearch flakiness). Standalone the same command works.
   Not yet resolved. Candidates: reduce sepp cpu (BUSCO always passes -c 16 to
   sepp), increase backsize / trainable sepp settings, `-F 15` fragment size.
3. pplacer segfault from sepp 4.5.5 (sepp issue #838). Not yet hit - test as
   described, fix with pplacer force-reinstall if it reproduces.
4. IMPORTANT TERMINAL HAZARD: BUSCO / HMMER write progress bars to the
   CONTROLLING TERMINAL (via /dev/tty), not just stdout. Even running under
   `setsid` with stdout+stderr redirected to files, launching BUSCO from an
   interactive shell still killed the opencode TTY and left it spamming
   escape sequences until `reset`. DO NOT run BUSCO interactively at all.
   The ONLY safe way is to run it as a batch job (sbatch) on a compute node,
   with all output going to the SLURM log file (`--output=/work/.../run_%j.log`),
   and then poll that log file from the interactive session. Never invoke
   `apptainer ... busco` directly from the interactive shell, even backgrounded.

## TODO
- Resolve sepp hmmsearch flaky failure (suspect: reduce `-c` given to sepp,
  or increase sepp `-F`/memory, or run sepp with 1 task).
- Once a single genome completes GREEN, run the 88-genome batch via SLURM.
- Add `--opt-out-run-stats` in scripts (BUSCO phones home, DATA upload).
- Separate SLURM wrapper script; compute nodes read the SIF ro.

## Current state (update)
- SIF rebuilt inside sbatch job with pplacer fix baked in. `busco --version`
  and `pplacer --version` both work, no segfault.
- ROOT CAUSE of the remaining blocker: sepp's auto-lineage placement step
  (seppJsonMerger.jar) crashes with `NumberFormatException: Cannot parse
  null string`. The new pplacer writes subset-tree edge labels as integers
  `{0},{1},...`, but the base tree uses support-value labels; the Java
  merger's bipartition map lookup fails (sepp 4.5.5 bug, BUSCO #834).
- SOLUTION (GREEN): specify the lineage explicitly with `-l eukaryota_odb12.2`
  instead of `--auto-lineage-euk`. This skips the sepp placement step
  entirely. Verified end-to-end on Capsicum:
  `C:86.4%[S:76.0%,D:10.4%],F:3.2%,M:10.4%,n:125` + full_table.tsv.
- Trade-off: auto-lineage auto-picks the best lineage; with explicit
  `eukaryota_odb12.2` we assume the (plant) genomes are eukaryotic, which
  is correct for this dataset. If per-genome auto-lineage is ever required,
  the sepp merger bug (#834) must be fixed upstream or the jar patched.

## TODO (final)
- Generalize the single-genome script into an 88-genome SLURM batch.
- Batch-mode BUSCO already loops over a directory of inputs (`-i seqs/`),
  producing one subdir per genome; add the full staging of all 88 genomes
  onto /work with `.fa` renames.