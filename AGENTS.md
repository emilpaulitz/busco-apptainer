# Development / Testing
- Follow strict red/green TDD. Run pytest before you change anything. Commit each phase separately in small increments.

# Data

Try this file first: you can start with `~/repos/agent-research/busco-emil/data/Capsicum_annuum_combined.fasta`.

# Documentation
- Document every task in numbered markdown files in `./tickets`. Name open tickets `NNNN-todo-*.md`. Rename to `NNNN-done-*.md` after completion, commit again. Stay brief, but record every hurdle you had to overcome.
- Clone repos and download official documentation instead of fetching it again and again. The BUSCO repo is available in `~/repos/busco`.

# HPC / SLURM
- ALWAYS pay attention to sbatch/srun warnings. In particular:
  - Do NOT set `--chdir` to a home directory; run jobs from `/work`.
  - Do NOT reference `/home/...` paths inside sbatch job scripts; compute
    nodes should only read/write `/work`. Sync files there instead.
- Login nodes start with a `login`/`jlogin` prefix. `n-hpc-caN` nodes are
  compute nodes: interactive jobs there (e.g. via `srun --pty bash`) run
  under a 2 GB RSS ulimit; memory-hungry steps (e.g. apptainer mksquashfs)
  get SIGKILLed. Run those inside a batch job with an explicit `--mem`
  allocation, or start the interactive session with a larger `--mem`.
- Compute nodes have NO direct outbound network; egress only works through
  the HTTP proxy. Job scripts must set it BEFORE any download or container
  bootstrap. `export https_proxy=[censored]` (Ask the user for the concrete link; also
  needed by `apptainer build` pulling `docker://` images and by curl/conda).
  Alternatively, download/fetch on the LOGIN node and stage artifacts into
  `/work` for batch jobs to consume (`localimage` builds over an existing
  SIF instead of `docker://` bootstraps).
- NEVER delete or overwrite an irreplaceable artifact before its replacement
  is fully built and verified. Build to a temp path and `mv` over only on
  success. Loss of the only copy (e.g. the base `.sif`) costs a full
  re-download/rebuild from zero.

# Collaboration
- DO NOT GUESS the user's intent on important issues (architectural or hard-to-reverse decisions). Ask with the `question` tool instead.
- You have no sudo rights. DO NOT ATTEMPT WORKAROUNDS! Always ask the user to run sudo commands. Write them as consecutively numbered bash scripts in `./scripts`.

# Refactoring rules
- For mechanical renames, derive the file list with `rg -l ... | xargs sed -i`.
