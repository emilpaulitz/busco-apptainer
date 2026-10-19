Thank you to Arne Neumann for providing this repository with a working BUSCO!

# BUSCO on the HPC via Apptainer (multi-user)

Workflow for running BUSCO 6.1.0 in Apptainer on the
University of Potsdam HPC. Each user builds their own SIF (Apptainer's
equivalent of a Docker image) under `/work/<user>/busco/`. 

The image is **fully fixed** (tickets 001/003): standalone pplacer (sepp
issue #838), sepp 4.5.6 `seppJsonMerger.jar` + `BuscoPlacer.py` edge-num
patch (BUSCO #834). Both explicit-lineage and `--auto-lineage-euk` can be
used.

## Setup and usage

```bash
git clone https://github.com/emilpaulitz/busco-apptainer
cd busco-apptainer

# 1. Build your own SIF container (batch job, takes ca. 5m).
# To check the progress of your batch jobs, see "Monitoring jobs and logs"
# below.
./scripts/submit.sh scripts/build_sif.sbatch

# 2. Stage inputs onto /work as .fa (rename .fasta to .fa avoids the sepp
#    "fasta"-in-path bug, BUSCO #432/#781)
python3 scripts/stage_genomes.py \
    /home/group/agnikoloski/genomes_for_arne/seqs_conform \
    /work/$USER/busco/all_seqs \
    --report /work/$USER/busco/stage_report.tsv

# 3. Test BUSCO on a single genome with --auto-lineage-euk.
./scripts/submit.sh scripts/run_busco.sbatch \
    /work/$USER/busco/all_seqs/Chloropicon_primus_combined.fa
#    ...or an explicit lineage instead (the array runs this with):
BUSCO_LINEAGE=eukaryota_odb12.2 ACCEPTANCE=1 \
    ./scripts/submit.sh scripts/run_busco.sbatch \
    /work/$USER/busco/all_seqs/Chloropicon_primus_combined.fa

# 4. Run an array of batch jobs over all genomes
#    (default: auto-lineage-euk;
#    the first run downloads cascade datasets on demand - for fully cached
#    runs set BUSCO_LINEAGE, e.g. eukaryota_odb12.2):
python3 scripts/make_chunks.py /work/$USER/busco/all_seqs /work/$USER/busco/chunks --chunk-size 8
./scripts/submit.sh scripts/run_busco_array.sbatch

# 5. Collect a summary TSV:
python3 scripts/collect_results.py /work/$USER/busco/results \
    --out /work/$USER/busco/busco_summary.tsv
```

**Always submit via `./scripts/submit.sh`**: Slurm reads `#SBATCH` directives
as literal text, so the wrapper injects the per-user
`--chdir/--output/--partition` (and mirrors `BUSCO_CPUS` to
`--cpus-per-task`) and stages the scripts into `$BUSCO_WORK/build/` so
compute nodes only ever read `/work`.

## Monitoring jobs and logs

```bash
squeue -u $USER                                    # array tasks show as <jobid>_<task>
sacct -j <jobid> --format=State,ExitCode,Elapsed   # finished jobs, incl. failures

# resource profile of a job (ticket 012: basis of the current defaults):
sacct -j <jobid> --format=JobID,Elapsed,AllocCPUS,TotalCPU,MaxRSS -X

# single jobs (run_busco.sbatch, build_sif.sbatch):
less /work/$USER/busco/logs/busco_<jobid>.log
# array jobs - one log per array task:
less /work/$USER/busco/logs/busco_array_<master>_<task>.log
```

- Measured resource profile (batch 1867567, 11 array tasks): MaxRSS
  2.5-3.3G, ~7 busy cpus, longest task 3:56. Hence the defaults
  `--mem=8G --cpus-per-task=8 --time=02:00:00` (array) and
  `--cpus-per-task=8 --mem=8G` with 12h for single jobs. If a job OOMs or
  times out, check its MaxRSS/TotalCPU with the `sacct` line above and
  override per submission, e.g. `submit.sh scripts/run_busco.sbatch
  --mem=16G /work/$USER/busco/all_seqs/BIG.fa`.

- The log names come from the `--output` pattern `submit.sh` injects:
  `%x_%j.log` for single jobs (`%x` = job name), `%x_%A_%a.log` for arrays
  (array master jobid + task id).
- A job that already left squeue may have failed - always check the SLURM
  log and `sacct` before collecting results. (`submit.sh` validates the
  `run_busco.sbatch` input path at submission time; other runtime errors
  only surface in the log.)
- BUSCO writes progress bars to `/dev/tty`; in batch jobs the SLURM log is
  the only output.

## Configuration (`scripts/lib.sh`)

| Variable | Default | Meaning |
|---|---|---|
| `BUSCO_WORK` | `/work/$(id -un)/busco` | your work root on /work |
| `BUSCO_SIF` | `$BUSCO_WORK/busco_6.1.0.sif` | container image |
| `BUSCO_DOWNLOADS` | `$BUSCO_WORK/downloads` | BUSCO lineage datasets |
| `BUSCO_RESULTS` / `BUSCO_CHUNKS` / `BUSCO_LOGS` / `BUSCO_SEQ` | `$BUSCO_WORK/…` | results, chunks, logs, staged inputs |
| `BUSCO_INPUT_DIR` | *(unset)* | datasets to stage from |
| `BUSCO_CPUS` | `8` | `busco -c` (and `--cpus-per-task` via submit.sh) |
| `BUSCO_LINEAGE` | *(unset)* | unset: `--auto-lineage-euk` (default); set: explicit `busco -l` |
| `BUSCO_PARTITION` | `all` | sbatch partition |
| `BUSCO_ARRAY_LIMIT` | *(unset)* | optional `%limit` on the auto `--array` |
| `BUSCO_PROXY` | *(unset)* | compute-node egress proxy |

Examples: `BUSCO_CPUS=32 submit.sh scripts/run_busco_array.sbatch` or
`BUSCO_WORK=/work/name/busco2 submit.sh scripts/build_sif.sbatch`.

## Files

- `scripts/lib.sh` - per-user configuration (sourced by every script).
- `scripts/submit.sh` - the only supported submission entry point.
- `scripts/build_sif.sh` / `build_sif.sbatch` - SIF build (direct / batch).
- `scripts/run_busco.sbatch` - single-genome run (explicit|autolineage).
- `scripts/run_busco_array.sbatch` - chunked SLURM array batch (resume-safe).
- `scripts/stage_genomes.py`, `make_chunks.py`, `collect_results.py` - input staging, chunking, result collection.
- `scripts/patches/BuscoPlacer.py` - BUSCO 6.1.0 edge-num fix, shipped via `%files`.
- `busco.def` - fully-fixed Apptainer definition.
- `scripts/diagnostics/` - historical one-off evidence (tickets 001-003), hardcoded paths left as-is.
- `scripts/fallback/` - archived zero-network seppfix patch-layer build.
- `tickets/` - per-task documentation.

## Layout on /work (per user)

```
/work/$USER/busco/
  busco_6.1.0.sif        # fully-fixed container (built by build_sif.sbatch)
  build/                 # submit.sh-staged copies (scripts, busco.def, patch)
  downloads/             # BUSCO datasets
  all_seqs/              # staged inputs (*.fa)
  chunks/chunk_NN/       # array inputs
  results/               # per-chunk / single outputs; single runs go to
                         # results/single/job_<jobid>/<genome>/ (re-runs are
                         # never overwritten; requeued jobs move old dirs to
                         # <genome>.bak_<timestamp>)
  logs/                  # SLURM logs (%x_%j.log; arrays %x_%A_%a.log)
```

## Why these workarounds exist (also in ./tickets)

1. **pplacer segfault** (sepp 4.5.5 bundles a broken pplacer; BUSCO/sepp
   issue #838): `%post` force-installs the standalone bioconda pplacer.
2. **sepp JSON merge crash** (#834): bundled 4.5.5 jar is incompatible with
   standalone pplacer >= 1.1.alpha17; replaced with the sepp 4.5.6 jar.
3. **BUSCO edge-num bug** (#834 twin): `BuscoPlacer._pick_dataset` hardcoded
   `p[0]` (alpha13 field order); patched file shipped via `%files`
   (ticket 003).
4. **`fasta` in path names** (#432/#781): sepp munges the literal string
   "fasta" to "jplace" in output dirs. Inputs are staged `.fasta` -> `.fa`.
5. **Terminal corruption**: BUSCO writes progress bars to `/dev/tty` and
   wrecks interactive terminals. **Always run BUSCO in a batch job** and
   read the SLURM log.
6. **Build memory limit**: interactive compute-node sessions run under a
   2 GB RSS ulimit; mksquashfs gets SIGKILLed. Build via `build_sif.sbatch`.
7. **Login vs compute nodes**: compute nodes only read/write `/work`;
   `submit.sh` stages everything there. Compute nodes reach the internet
   only via the proxy (exported by the build/autolineage scripts).
