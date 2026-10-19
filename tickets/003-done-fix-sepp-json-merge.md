# 003 - Follow-up: fix sepp JSON merging (seppJsonMerger.jar) to restore auto-lineage

## Problem
BUSCO's `--auto-lineage-euk` runs sepp placement, whose final step
(`seppJsonMerger.jar`) crashes with:

```
java.lang.NumberFormatException: Cannot parse null string
    at phylolab.taxonamic.PPlacerJSONMerger.relabelJson(PPlacerJSONMerger.java:172)
```

Root cause (from ticket 001): the new/standalone `pplacer` writes subset-tree
edge labels as **integers** (`{0},{1},...`), while the base (reference) tree uses
**support-value** labels. The Java merger builds a bipartition->edge-number map
from each tree; the subset-tree integer labels don't exist in the base-tree map,
so `labelMap.get(...)` returns null and `new Integer(null)` throws.

Affects sepp 4.5.5; matches upstream BUSCO issue #834. We worked around it by
passing an explicit `-l eukaryota_odb12.2` (skips sepp). That is fine for these
plant protein sets, but auto-lineage remains broken for general use.

## Refined root cause (2026-09-08, two independent breakages, both in 4.5.5)
1. pplacer >= 1.1.alpha17 writes jplace edge labels in braces `{N}` (jplace
   spec style); sepp's trees use brackets `[N]`. 4.5.5's
   `edgeNumPattern = .*[\[]([0-9]*)[\]]` cannot parse `{N}` -> getEdgeNum
   returns "?" -> labelMap lookups miss -> `new Integer(null)` NFE.
2. alpha17 reorders the placements `p` fields: `["distal_length",
   "edge_num", ...]` (verified in a preserved jplace). 4.5.5 hardcodes
   edge_num at index 0 and distal_length at index 1.
sepp v4.5.6 (Aug 2026) fixes exactly both: regex widened to `[\[\{]`, and `p`
positions read from the jplace `fields` array (commit 1f724c7). Its release
notes name the alpha13 -> alpha17 change verbatim, and the bioconda 4.5.6
recipe declares `pplacer >=1.1.alpha17` as a run dep - i.e. 4.5.6 is built to
pair with the standalone pplacer we force-install in `busco.def`.

## Decision
- Fix strategy: **jar swap only** (option 2, scoped down). Overwrite the
  bundled 4.5.5 `seppJsonMerger.jar` with the prebuilt v4.5.6 jar (shipped in
  the source tarball at `tools/merge/seppJsonMerger.jar`, no Java build) in
  `%post` of `busco.def`.
  - NOT a full sepp 4.5.6 upgrade: busco 6.1.0 pins sepp 4.5.5; a package
    upgrade into `/usr/local` pulls `pasta` and churns the env busco itself
    lives in. The jar is the only alpha17-compat fix.
- Keep the explicit-`-l` workaround until the fix is validated end-to-end.

## Key facts for the isolated replay (no sepp rerun needed)
- Failing run's inputs survived: 12 subset `.jplace` files under
  `/work/neumann19/busco/test_odb12/BUSCO_res/Capsicum_annuum_combined.fa/
  auto_lineage/run_eukaryota_odb12/sepp_tmp_files/output.2pbmiiwn/root/P_*/`,
  exact invocation in `run_odb12_1866053.log:264`
  (`java -jar /usr/local/bin/seppJsonMerger.jar - - <out>` = stdin mode).
- stdin stream format (sepp `exhaustive.py:271-288`): line 1 = full labeled
  tree `;`-terminated; then per placement job `<labeled subset tree>;\n<jplace
  path>`; blank line ends stream.
- sepp labels edges 0..n-1 in dendropy postorder after `resolve_polytomies()`
  (`tree.py:412`, `exhaustive.py:326-329`); `compose_newick(labels=True)`
  emits `name:len[label]`.
- The merger maps jplace `{N}` -> subset-tree `[N]` labels **by bipartition
  within each subset** (`mapTrees`); the first (full-tree) line only feeds
  `mainEdgeLen` for the distal_length clamp. Therefore a self-consistent
  single-jplace replay (line 1 = line 2 = the jplace tree re-labeled sepp-style
  `[0..m]` postorder) exercises every fixed code path without replicating
  sepp's subset decomposition.
- Edge labels of the per-subset trees are lost ({N} is pplacer's own
  numbering), so the replay is self-consistent synthetic; the real full-tree
  labeling is only exercised by the end-to-end run (phase 4).

## Plan (TDD; batch jobs only, never interactive; /work paths only)
1. **RED**: `scripts/10_*` stream-builder + sbatch replay of all 12 preserved
   jplaces against the SIF's bundled 4.5.5 jar -> expect
   `NumberFormatException` on every stream (reproduces log:264-270).
2. **GREEN (isolated)**: extract `tools/merge/seppJsonMerger.jar` from the
   sha256-verified sepp v4.5.6 tarball onto /work, rerun the replay with
   container java -> valid merged JSON per jplace; `scripts/11_*` verifies
   every edge_num translation bipartition-by-bipartition.
3. **Bake**: `busco.def` `%post` downloads the tarball, verifies sha256,
   overwrites `/usr/local/bin/seppJsonMerger.jar`; rebuild SIF in a batch job
   with explicit `--mem` (mksquashfs SIGKILL hazard), from /work.
4. **Acceptance**: sbatch BUSCO `--auto-lineage-euk` on the Capsicum input ->
   no NFE, lineage auto-selected, `short_summary` produced. Rename ticket
   `003-done`, commit.

## Relevant code / files
- Java source: `tools/merge/src/phylolab/taxonamic/PPlacerJSONMerger.java`
  (in smirarab/sepp; 4.5.5 crash at relabelJson ~172; fixed jar committed at
  `tools/merge/seppJsonMerger.jar`).
- Local clone: `~/repos/sepp` (v4.5.6 tag). Tarball sha256:
  `e4aae4908b33d54d34c8796bc1f5aed38e8969c411102d713da075a0d7832560`.
- sepp internals: `sepp/exhaustive.py:271-292` (stream), `sepp/tree.py:412`
  (edge labeling), `sepp/jobs.py:594-623` (MergeJsonJob stdin mode).
- sepp 4.5.6 on bioconda is noarch; busco 6.1.0 conda recipe pins sepp 4.5.5.

## Acceptance
`--auto-lineage-euk` on the Capsicum input completes without the
`NumberFormatException`, producing a `short_summary` (not "Run failed").

## Second blocker discovered during acceptance (BUSCO-side twin bug)
With correct placements in `output_placement.json`, BUSCO 6.1.0 still
selected `euarchontoglires` (a MAMMAL lineage) for Capsicum. Root cause:
`BuscoPlacer._pick_dataset` hardcodes `individual_placement[0]` as the
edge_num (BuscoPlacer.py:216 in 6.1.0) - the same alpha13-era field-order
assumption as the old sepp jar. With modern pplacer output, p[0] is
distal_length; 92 of 251 placements had INTEGRAL distal_lengths (JSON int
`0`), whose `[%s]` regex matches arbitrary tree edge labels
(e.g. `[0]` -> taxid 110931) -> garbage lineage selection. The 159 float
distal_lengths never match (hence only 22 of 92 hits counted).
Verified no upstream fix: BUSCO 6.1.0 (2026-06-05) is the latest and still
hardcodes index 0 (checked GitLab commit history for BuscoPlacer.py).
Fix: `scripts/patches/BuscoPlacer.py` (base byte-identical to upstream
6.1.0; reads the edge_num position from the jplace `fields` array, falls
back to 0), shipped via `busco_seppfix.def` %files + sha256 + py_compile.
After the patch: `Lineage solanales is selected, supported by 72 markers
out of 84` - biologically correct (Capsicum is Solanales).

## TODO (follow-up)
- Report both halves upstream: sepp 4.5.5 jar + BUSCO 6.1.0 BuscoPlacer
  (GitLab ezlab/busco), referencing BUSCO #834.
  -> Drafted in `tickets/004-todo-comment-busco-issue-834.md` (comment on
  the existing #834) and `tickets/005-todo-report-busco-placer-edge-num-bug.md`
  (new issue for the still-unfixed BuscoPlacer bug).

## Acceptance evidence (2026-09-08)
- `--auto-lineage-euk` on Capsicum (job 1866262, rebuilt SIF):
  no NumberFormatException, sepp placement succeeded,
  `Lineage solanales is selected, supported by 72 markers out of 84`,
  final run `C:69.7%[S:68.3%,D:1.4%],F:2.6%,M:27.7%,n:12372`,
  short_summary produced, BUSCO_EXIT=0.
- Replay: old jar NFE 12/12 (RED); 4.5.6 jar merges 12/12, all 251
  placements' edge_num translations bipartition-verified (GREEN).

## Status: DONE

## Progress (commit history)
- Plan committed (root cause refined to the two breakages above).
- Phase 1 RED: `scripts/10_build_merger_streams.py` (reconstructs the merger
  stdin stream from the preserved jplaces; sepp-style postorder `[N]`
  relabeling, offset +1000 so the bipartition map is non-identity) +
  `scripts/11_sepp_merger_replay.sbatch`. Old jar: 12/12 NFE, identical
  stack (`relabelJson:172`). Committed.
- Phase 2 GREEN: sha256-verified sepp v4.5.6 tarball (matches bioconda
  recipe), jar staged to /work. New jar: 12/12 merged; `scripts/12_verify_
  merged_json.py` proves every edge_num translation (pplacer 0-based ->
  +1000 label space) is bipartition-consistent (320 placements). Committed.
- Phase 3 (in progress): jar-swap %post added to busco.def. Hurdles below
  forced a re-think of the build path.

## Hurdles
1. Compute-node egress: `curl -sL` to github failed silently in a batch job
   -> all four endpoints time out WITHOUT the proxy. RESOLVED: compute nodes
   reach the internet only via `export https_proxy=http://proxy2.uni-
   potsdam.de:3128`. Documented in AGENTS.md; all build scripts now export
   it. (Login node egress works without it.)
2. SIF loss: the first failed rebuild ran `rm -f` on the only SIF copy
   before building -> full re-pull needed. Rule added to AGENTS.md:
   never delete an irreplaceable artifact before its replacement is fully
   built and verified; 01 now builds to a temp path and replaces only on
   success.
3. Wrong base for the localimage patch: after re-pulling, the patch SIF was
   layered on the RAW upstream image, silently losing the ticket-001 %post
   pplacer fix (bundled pplacer segfaults, exit 139). The acceptance run
   then failed EARLIER, at pplacer subproblems, not the merger - a useful
   RED. Full canonical rebuild via 02 (proxy-enabled) restores both fixes
   in one image.
4. sbatch hardening: 02 had no `--chdir` (defaults to /home!) and referenced
   /home paths - exactly the AGENTS.md anti-patterns; now /work-only.
5. Zero-network fallback kept: `scripts/busco_seppfix.def` (localimage over
   an existing good SIF + %files'd jar) for when even the proxy path is
   unavailable.
