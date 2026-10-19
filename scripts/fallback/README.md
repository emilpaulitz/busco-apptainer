# fallback/ - zero-network seppfix build (archived, unsupported)

Archived in ticket 006: the canonical `busco.def` build (scripts/build_sif.sh
+ scripts/build_sif.sbatch) works reliably through the HPC proxy and produces
the fully-fixed image (standalone pplacer + sepp 4.5.6 jar + BuscoPlacer.py
patch). This localimage patch-layer path is kept for the case where
compute-node egress via the proxy ever becomes unavailable.

To resurrect it:
1. Copy it back to `scripts/`.
2. Replace the hardcoded `neumann19` paths with your `$BUSCO_WORK`.
3. Stage the 5 artifacts into `$BUSCO_WORK/sepp_fix/`:
   - `seppJsonMerger-4.5.6.jar` (from the sha256-verified sepp v4.5.6 tarball,
     see ticket 003), `pplacer`, `guppy`, `rppr` (bioconda standalone
     pplacer 1.1.alpha22), and `scripts/patches/BuscoPlacer.py` from this repo.
4. Build in a batch job with `--mem` (mksquashfs SIGKILL hazard).

Files:
- 13_build_sif_seppfix.sbatch - batch build wrapper
- busco_seppfix.def           - localimage patch layer (base SIF + %files)
