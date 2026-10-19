# 004 - Follow-up: comment on BUSCO issue #834 (sepp jar half of the bug)

## Goal
Post our root-cause analysis + working fix as a comment on
https://gitlab.com/ezlab/busco/-/issues/834
("SEPP placement fails in BUSCO due to null values in .jplace files").
No sepp issue needed: the jar fix is already upstream in sepp v4.5.6.

## Draft (paste-ready)

> We hit the same `NumberFormatException: Cannot parse null string`
> (`PPlacerJSONMerger.relabelJson:172`) with BUSCO 6.1.0 / sepp 4.5.5 on an
> HPC (Apptainer container, standalone pplacer from bioconda). We root-caused
> it; two notes that may save others some time:
>
> **1. The jplace files are not actually corrupt.** The `null` in the error
> comes from *inside* the merger: sepp 4.5.5's `seppJsonMerger.jar` is
> incompatible with the output of standalone `pplacer >= 1.1.alpha17`
> (bioconda's `pplacer` package), in two independent ways:
>
> - pplacer >= 1.1.alpha17 reordered the columns of the `p` array: the
>   `fields` line reads `["distal_length", "edge_num", ...]`, while sepp
>   4.5.5's jar hardcodes `pr.getString(0)` as edge_num and
>   `pr.getDouble(1)` as distal_length. (sepp 4.5.6's release notes describe
>   exactly this: "The order changed from the bundled pplacer (v1.1.alpha13)
>   to the later version (v1.1.alpha17)".)
> - The tree field uses `{N}` edge labels (jplace-spec style) instead of
>   sepp's `[N]`; the 4.5.5 jar's edge-number regex only parses `[N]`, so
>   every bipartition lookup misses and `new Integer(null)` throws.
>
> **2. Fix:** use sepp 4.5.6's `seppJsonMerger.jar` (it parses both label
> styles and reads column positions from the `fields` array). We verified
> end-to-end: sepp 4.5.5 jar + standalone pplacer 1.1.alpha22 crashes with
> this exact stack; swapping in the 4.5.6 jar (with `pplacer` 1.1.alpha22)
> merges all placement subsets correctly. In a container this is just
> overwriting the bundled jar with the one from the sepp v4.5.6 source
> tarball (`tools/merge/seppJsonMerger.jar`), no rebuild of sepp needed.
>
> **One more caveat:** with the jar fixed, `--auto-lineage-euk` still picks
> a wrong lineage because of a second, BUSCO-side instance of the same
> field-order assumption (`BuscoPlacer._pick_dataset`, hardcodes
> `individual_placement[0]`). Details in a separate issue.

## Evidence to link (if asked)
- Failing run log with the exact stack:
  `/work/neumann19/busco/run_odb12_1866053.log:264-270` (login node).
- Isolated replay (RED 12/12, GREEN 12/12 + bipartition verification):
  `scripts/10_build_merger_streams.py`, `scripts/11_sepp_merger_replay.sbatch`,
  `scripts/12_verify_merged_json.py` (repo).

## How to post
GitLab web UI (needs ezlab/busco access) or `glab issue view 834` + comment.
Ticket is DONE once the comment is posted (and ideally a BUSCO maintainer
confirms).

## Status: TODO
