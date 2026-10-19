# 005 - Follow-up: report BUSCO BuscoPlacer edge_num bug upstream (new issue)

## Goal
File a new issue on https://gitlab.com/ezlab/busco (needs an account): the
`--auto-lineage` / `--auto-lineage-euk` dataset picker hardcodes the jplace
`p`-array column position, so with standalone `pplacer >= 1.1.alpha17` it
selects a biologically wrong lineage. Still unfixed in BUSCO 6.1.0
(latest; verified via GitLab commit history of `src/busco/BuscoPlacer.py` —
only touched at release commits, none after 6.1.0 fix this).

## Draft (paste-ready)

**Title:** auto-lineage selects wrong lineage: BuscoPlacer._pick_dataset assumes edge_num is the first column of the jplace "p" array

**Summary:**
`BuscoPlacer._pick_dataset` reads the placement's edge number as
`individual_placement[0]` (`src/busco/BuscoPlacer.py`, line 216 in BUSCO
6.1.0). With the bundled pplacer that sepp 4.5.5 shipped
(v1.1.alpha13), the `p` array indeed starts with `edge_num`. With standalone
pplacer >= 1.1.alpha17 (e.g. bioconda `pplacer` 1.1.alpha22, which is also
what sepp 4.5.6 pairs with), the column order changed to
`["distal_length", "edge_num", "like_weight_ratio", "likelihood",
"pendant_length"]` — `p[0]` is now the distal length.

Consequences, observed with BUSCO 6.1.0 + sepp 4.5.6 + pplacer 1.1.alpha22
(`--auto-lineage-euk`, eukaryota_odb12.2):

- float distal lengths never match the `[%s]` edge-label regex in the
  merged tree, so those placements are silently skipped;
- integral distal lengths (JSON-serialized as integers, e.g. `0`) DO match
  arbitrary tree edge labels. Example: 92 of our 251 placements had
  distal_length `0`, and the pattern `\[0\]` matched tree edge label `0`,
  extracting whatever taxid precedes it in the newick — a random reference
  taxon.

The lineage is then picked from that garbage: for a pepper genome
(Capsicum annuum) BUSCO logged
`Lineage euarchontoglires is selected, supported by 22 markers out of 22`
— a mammal lineage. The placements themselves are correct (we verified
bipartition-wise that all placed edges are in plant clades).

The code's own comment already anticipates this class of breakage:
"if this pattern is inconsistant with pplacer version, it may break
buscoplacer."

**Suggested fix** (we patched it locally and `--auto-lineage-euk` then
correctly selects `solanales`, supported by 72/84 markers, for the same
input):

```python
        node_weight = {}
        n_p = 0
        # read the column position from the jplace header instead of
        # hardcoding 0 (field order changed in pplacer >= 1.1.alpha17)
        try:
            edge_num_idx = data["fields"].index("edge_num")
        except (KeyError, ValueError):
            edge_num_idx = 0
        for placement in placements:
            n_p += 1
            for individual_placement in placement["p"]:
                # find the taxid in tree
                node = individual_placement[edge_num_idx]
```

**Environment:**
- BUSCO 6.1.0 (also present in master), python 3.12
- sepp 4.5.6 (seppJsonMerger.jar), standalone pplacer 1.1.alpha22 (bioconda)
- Linux x86_64 HPC, Apptainer 1.2.5, eukaryota_odb12.2 (2026-05-13)
- Input: Capsicum annuum proteins, `--auto-lineage-euk -m proteins -c 16`

Related: the sepp 4.5.5 `seppJsonMerger.jar` crashed on the same field-order
change (see issue #834); that half is fixed upstream in sepp 4.5.6, this
BUSCO-side half is still open.

## Evidence to link (if asked)
- Wrong-selection log: `/work/neumann19/busco/logs/busco_autolineage_1866257.log`
  ("Lineage euarchontoglires is selected, supported by 22 markers out of 22").
- Correct-selection log after patch:
  `/work/neumann19/busco/logs/busco_autolineage_1866262.log`
  ("Lineage solanales is selected, supported by 72 markers out of 84").
- Patched file (base byte-identical to upstream 6.1.0):
  `scripts/patches/BuscoPlacer.py` (repo).

## How to post
GitLab web UI → ezlab/busco → New issue (or `glab issue create -R ezlab/busco`).
Ticket is DONE once the issue is filed (record the issue URL here).

## Status: TODO
