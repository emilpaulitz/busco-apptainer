# diagnostics/ - historical, one-off evidence from tickets 001-003

These scripts reproduce the ticket 001-003 debugging journey (odb12
experiment, jplace/tree inspection, seppJsonMerger stream building/replay/
verification). They are NOT part of the supported workflow.

- Paths inside are hardcoded to `/work/neumann19/...` from the era when the
  repo was single-user; they are deliberately left untouched as evidence and
  are excluded from the no-hardcoded-paths lint test
  (`tests/test_no_hardcoded_paths.py`).
- 04_run_busco_odb12.sh      - first full-DB run (ticket 001)
- 05_inspect_jplace.sh       - jplace file inspection (ticket 001)
- 06_inspect_tree.sh         - base-tree edge label inspection (ticket 003)
- 10_build_merger_streams.py - reconstruct seppJsonMerger stdin streams (RED, ticket 003)
- 11_sepp_merger_replay.sbatch - replay streams against old/new jar (RED/GREEN, ticket 003)
- 12_verify_merged_json.py   - bipartition-verify edge_num translations (ticket 003)
