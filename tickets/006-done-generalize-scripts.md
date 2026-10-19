# 006 - Generalize scripts for multi-user use (drop neumann19 hardcodes)

## Problem
All Apptainer-build and sbatch scripts hardcode `/work/neumann19/...` (74
references). Colleague `paulitz` (same `agnikoloski` group) and other group
members cannot use them.

## Decisions (interview 2026-09-08)
1. **Distribution**: new internal GitLab
   `[censored]`; `origin`
   retargeted, branch pushed as `main`.
2. **Artifacts**: every user builds their own SIF into `/work/<user>/busco`
   via the sbatch build path (proxy export; mksquashfs needs batch-job `--mem`).
3. **Config**: `scripts/lib.sh`, env-var based, zero-edit default
   `BUSCO_WORK=/work/$(id -un)/busco`; every knob overridable
   (BUSCO_SIF/DOWNLOADS/RESULTS/CHUNKS/LOGS/SEQ, INPUT_DIR, CPUS, MEM,
   PARTITION, CHUNK_SIZE, LINEAGE, MODE, ARRAY_LIMIT).
4. **sbatch paths**: Slurm 26.05 reads `#SBATCH` directives as literal text
   (verified in sbatch man page) -> `scripts/submit.sh` wrapper injects
   `--chdir=$BUSCO_WORK --output=$BUSCO_WORK/logs/%x_%j.log` and passes
   through extra sbatch args; auto-computes `--array=0-N` from chunk dirs
   (overridable).
5. **Deliverable**: ONE fully-fixed image. `busco.def` gains the
   `BuscoPlacer.py` patch via `%files` from the repo (built from repo root;
   CWD-relative `%files` is documented behavior, verified by the first build
   job - failures are loud and pre-network).
6. **Fallback**: zero-network seppfix path (13 + busco_seppfix.def) archived
   to `scripts/fallback/` (canonical build works via proxy; git preserves it).
7. **Run surface**: 1 parameterized single-genome runner
   (MODE=explicit|autolineage, input arg, optional acceptance check) + the
   array batch. 03/07/09/14 retire.
8. **Diagnostics**: 04/05/06/10/11/12 -> `scripts/diagnostics/` untouched,
   excluded from the lint test (historical ticket evidence).
9. **Input default**: `BUSCO_INPUT_DIR=[censored]`
   (group-readable, user-independent).
10. **Tests**: no-hardcoded-paths lint (RED first) + `bash -n` over all
    scripts + lib.sh unit tests. Cluster acceptance = manual sbatch runs.

## Phases (each: pytest green + own commit)
1. Move diagnostics.
2. RED: lint + syntax + lib tests.
3. GREEN: lib.sh + submit.sh + script bodies rewritten.
4. Build path: busco.def %files patch, build_sif.sh/.sbatch; cluster build
   verification (busco/pplacer versions, sha256 checks).
5. Run consolidation: run_busco.sbatch + run_busco_array.sbatch; cluster
   smoke (Capsicum explicit + autolineage).
6. Archive fallback.
7. README rewrite, ticket rename, origin -> gitup, push main.

## Status: DONE

## Results (2026-09-08)
- Repo-side refactor complete: 54 pytest tests green, incl. the
  no-hardcoded-paths lint over the supported set (scripts top-level,
  busco.def, README). Supported surface: lib.sh, submit.sh, build_sif.sh,
  build_sif.sbatch, run_busco.sbatch, run_busco_array.sbatch,
  stage_genomes.py, make_chunks.py, collect_results.py, busco.def,
  pplacer_bin/ (vendored), patches/, diagnostics/, fallback/.
- Cluster acceptance, all batch jobs:
  - build (job 1866501): OK, SIF at /work/neumann19/busco/busco_6.1.0.sif.
  - verify (1866538): BUSCO 6.1.0; pplacer exits 0 (no segfault); jar
    sha256 cd70b622..., BuscoPlacer.py 734f5ff9..., pplacer/guppy/rppr
    687a/06ee/d5eb... - all identical to the ticket-003-validated image.
  - run_busco explicit (1866539): C:86.4%[S:76.0%,D:10.4%],F:3.2%,M:10.4%,
    n:125 - exact ticket-001/002 match.
  - run_busco autolineage BUSCO_FORCE=1 ACCEPTANCE=1 (1866571): "Lineage
    solanales is selected, supported by 72 markers out of 84";
    C:69.7%[S:68.3%,D:1.4%],F:2.6%,M:27.7%,n:12372; ACCEPTANCE PASSED.
  - run_busco_array --array=0 (1866601): COMPLETED in 6s; 6 genomes
    SKIP (resume-safe), the 2 known-bad inputs failed in isolation (old
    ticket-002 decision), per-genome loop + failure log intact.

## Hurdles
1. sbatch executes the job from /var/spool/slurmd/job<id>/slurm_script, so
   `$0`-based sibling resolution is impossible inside batch jobs (probe job
   1866477 failed instantly). Fix: everything resolves via BUSCO_LIB (env
   from submit.sh); helper scripts sit next to lib.sh in the staged dir.
2. Probe payoff: apptainer 1.2.5 DOES resolve %files sources relative to the
   CWD of `apptainer build` (job 1866501 log) - the localimage From probe was
   made moot by archiving the fallback, but the relative %files behavior is
   now confirmed and used by busco.def (patch + vendored pplacer).
3. Proxy flakiness escalated from transient to systemic: micromamba could
   not load anaconda.org repodata (conda-forge/noarch, bioconda/noarch
   "shard not visited" -> "Subdir not loaded") through the proxy in 3
   retries, and a plain curl to micro.mamba.pm failed with exit 7 between
   builds (while 765MB quay.io layer pulls kept succeeding). Fix: dropped
   the conda solve entirely and vendored the 3 sha256-verified standalone
   pplacer binaries into the repo (pplacer_bin/), %files'd them over the
   base's broken alpha13. %post now only downloads the small sepp tarball
   (with curl --retry). Build is near-hermetic and byte-identical in the
   critical components to the validated ticket-003 image.
4. submit.sh arg-order bug (found by the array smoke, job 1866573 FAILED):
   user sbatch options appended after the job path were treated as SCRIPT
   args by sbatch - --array=0 was silently ignored and the job ran plain
   (SLURM_ARRAY_TASK_ID unbound). Fix: split leading '-' args into sbatch
   options (before the job path), rest into script args; shim re-verified.
5. run_busco rerun collision: BUSCO refuses existing run dirs; submitting
   autolineage right after explicit with the same input fails with
   "...already exists". Fix: BUSCO_FORCE=1 knob (explicit overwrite).
6. Process lesson: poll loops must watch for FAILURE markers
   (BUSCO_EXIT=nonzero/FAILED) as well as success ones, or they spin for
   hours on an already-failed job.
