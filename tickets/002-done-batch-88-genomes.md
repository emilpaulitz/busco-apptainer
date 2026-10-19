# 002 - Batch-run BUSCO on the 88 genomes

## Goal
Run BUSCO on all 88 genomes in
`[censored]` (currently `*.fasta`,
~1.4G), in Apptainer on compute nodes, using the verified working command
(explicit lineage, proteins mode, no auto-lineage/sepp).

## Status: DONE

## Results (2026-09-08)
Summary TSV: `/work/neumann19/busco/busco_summary.tsv` (88 rows).
- 45 ok: median complete 96.8%, 36 genomes C>=90, 8 genomes 50<=C<90,
  1 genome C<50 (min 23.2%). Top: Chlamydomonas_reinhardtii C:100%,
  Arabidopsis_thaliana C:99.2% (but S only 44%, D 55.2%),
  Aristolochia_fimbriata C:99.2%.
- 36 EMPTY (C:0.0%, M:100%) - matches the colleague's warning; mostly
  algae/bryophytes whose "combined" sets are not suitable protein inputs.
- 7 FAILED with duplicate sequence IDs in the FASTA (BUSCO refuses:
  "Duplicate of sequence >rps12|..." etc.): Acer_yangbiense,
  Apium_graveolens, Cannabis_sativa, Chlorella_vulgaris, Cucumis_sativus,
  Pyramimonas_parkeae, Tetracentron_sinense. User decision: leave failed,
  no data modification. List: `/work/neumann19/busco/failed_genomes_all.txt`.
- Walltimes: chunks of 8 took 1:17-5:23 min (Triticum chunk slowest);
  whole batch done in minutes of cluster time.

## Verified working single-genome recipe (from ticket 001)
```
apptainer exec --bind /work:/work /work/neumann19/busco/busco_6.1.0.sif busco \
    -i SEQDIR -l eukaryota_odb12.2 -m proteins -c 16 -o BUSCO_res \
    --out_path OUT --download_path /work/neumann19/busco/downloads \
    --opt-out-run-stats
```
Result on Capsicum: C:86.4%[S:76.0%,D:10.4%],F:3.2%,M:10.4%,n:125.

## Rationale: why copy + rename onto /work
1. HPC rule: compute nodes only read/write `/work`; sbatch scripts must not
   reference `/home/...`. It must be a real copy, not a symlink: BUSCO
   copies/dereferences inputs into its tmp dir, so a link would still pull
   I/O from `/home` on the compute node.
2. Rename `.fasta` -> `.fa`:
   - Insurance against the sepp path-munging bug (BUSCO #432/#781) where the
     literal "fasta" in paths breaks placement dirs (ticket 001 hurdle 1).
     Batch mode uses explicit lineage so sepp never runs, but the rename is
     cheap and keeps `--auto-lineage` re-runs safe.
   - Output subdirs inherit the input basename *including extension*
     (`src/busco/BuscoRunner.py:294-303`), so with `.fasta` kept, every
     output path would contain "fasta" too.

## Findings (2026-09-08)
- 88 files, all `<Species>_combined.fasta`, no basename collisions after the
  extension swap.
- 4 names have interior dots (`Beta_vulgaris_subsp._vulgaris`,
  `Coccomyxa_sp._Obi`, `Derbesia_sp._WEST4838`, `Scenedesmus_sp._PABB`).
  Harmless in proteins mode: the `split(".")[0]` in
  `src/busco/busco_tools/hmmer.py:641` applies to internal files, not user
  filenames. Staged verbatim.
- Sequence counts span 61 (Solanum_aturense) to 135,172 (Triticum_aestivum);
  a few big genomes dominate walltime.
- 1.4G total; `/work` has 6.5T free.

## Decisions
- Chunked SLURM array: 11 tasks x 8 genomes, `--cpus-per-task=16`,
  `--mem=32G`, batch mode per chunk (`-i chunk_dir`).
- Staging: verbatim rename, only `.fasta` -> `.fa`.
- Dataset `eukaryota_odb12.2` already downloaded in ticket 001: reuse
  `--download_path`, add `--offline` (avoids 88 concurrent phone-homes).
- Per-genome `BuscoError` is caught inside batch mode
  (`BuscoRunner.py:345-383`; logged as "Run failed; check logs" in
  `batch_summary.txt`), so one bad genome does not kill its chunk; a crashed
  chunk only costs its own array task.

## Steps
1. Stage all 88 inputs to `/work/neumann19/busco/all_seqs` as `<name>.fa`
   (verbatim), sha256 spot-check, per-file sanity report (record count,
   protein alphabet) - colleague warned "not all will give meaningful
   results".
2. Split into 11 chunk dirs of 8 (deterministic order) and an sbatch array
   (`--array=0-10`, 16 cores, 32G each). Batch jobs only: BUSCO/HMMER write
   progress bars to /dev/tty, never run interactively (ticket 001 hurdle 4).
   Logs to `/work/neumann19/busco/logs/`.
3. Run the verified recipe per chunk + `--offline`; collect runtimes.
4. Collect per-genome short_summary + full_table into one TSV; flag
   trivial/empty results; rename this ticket to `002-done-*`.

## Hurdles
- BUSCO batch mode is strictly sequential (`BuscoRunner.py:284`): `-i dir`
  gives zero cross-genome parallelism; all parallelism comes from the array.
- TTY hazard is not limited to BUSCO: even plain `sinfo`/`scontrol` queries
  from the interactive session trashed the opencode terminal with escape
  codes (2026-09-08). Policy: redirect ALL SLURM/cluster command output to a
  file under /tmp/opencode and Read it; never let it stream to the TTY.
- beegfs `du` under-reports freshly written data (staged dir showed 298M
  until block allocation caught up; `stat` byte sums matched exactly, 1.4G).
  Verify staging with `stat -c %s`, not `du`.
- First array run: 9/11 chunks OK, 2 FAILED because `Apium_graveolens` and
  `Nelumbo_nucifera` begin with blank lines; biopython's strict `fasta`
  parser raises ValueError (Bio/SeqIO/FastaIO.py:202, reached from
  `Analysis.py:124`), BUSCO converts any non-BuscoError into
  BatchFatalError (`BuscoRunner.py:386-387`) killing the whole chunk - and
  then its own handler crashes (`TypeError: __str__ returned non-string`,
  run_BUSCO.py:112). Fixes: staging now strips leading blank lines
  (TDD, `stage_genomes.clean_leading_blank_lines`); offending staged files
  cleaned in place. Script 08 rewritten to ONE busco invocation per genome
  with per-genome failure log, so a bad genome cannot kill a chunk again.
- BUSCO batch mode iterates `os.listdir` UNSORTED (`BuscoRunner.py:275`),
  so per-genome order inside a chunk is arbitrary (chunk_0 died on its
  first-picked file before processing anything; chunk_5 lost only its
  last 2). The per-genome loop in script 08 is explicitly sorted.
- Resume-safe: failed tasks are resubmitted with `sbatch --array=0,5`;
  script 08 skips genomes whose short_summary already exists (works for
  both the old batch-mode layout `chunk_NN/BUSCO_res/<g>.fa/` and the new
  per-genome layout `chunk_NN/<g>/`).
- Process lesson: a `git reset --hard` in a command chain discarded an
  uncommitted edit of script 08 (it was unstaged during the previous
  commit); had to rewrite it. Stage/commit files before any reset.
