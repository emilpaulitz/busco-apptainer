#!/usr/bin/env python3
"""Verify a seppJsonMerger output against its source jplace (ticket 003).

For every placement, the old edge_num (pplacer's `{N}` label space) and the
merged edge_num (the `[N]` label space of the stream's tree) must sit on the
same bipartition, i.e. the clade below both edges must be the same taxon set.
Also checks the merged tree field, field layout, and placement count.
"""
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from importlib import import_module

builder = import_module("10_build_merger_streams")


def label_to_clade(root):
    acc = {}
    if root.label is not None:
        acc[root.label] = builder.clade(root)
    for child in root.children:
        acc.update(label_to_clade(child))
    return acc


def main():
    jplace_path, merged_path = sys.argv[1], sys.argv[2]
    with open(jplace_path) as fh:
        jplace = json.load(fh)
    with open(merged_path) as fh:
        merged = json.load(fh)

    jplace_root = builder.parse_newick(jplace["tree"])
    merged_root = builder.parse_newick(merged["tree"])

    jmap = {}
    if jplace_root.label is not None:
        jmap[jplace_root.label] = builder.clade(jplace_root)
    for child in jplace_root.children:
        jmap.update(label_to_clade(child))

    mmap = {}
    if merged_root.label is not None:
        mmap[merged_root.label] = builder.clade(merged_root)
    for child in merged_root.children:
        mmap.update(label_to_clade(child))

    jfields = jplace["fields"]
    mfields = merged["fields"]
    je, me = jfields.index("edge_num"), mfields.index("edge_num")

    n_old = n_new = 0
    for jpl, mpl in zip(jplace["placements"], merged["placements"]):
        assert jpl.get("n") == mpl.get("n") and jpl.get("nm") == mpl.get("nm"), (
            "placement names differ: %r vs %r" % (jpl.get("n", jpl.get("nm")),
                                                  mpl.get("n", mpl.get("nm"))))
        for jp, mp in zip(jpl["p"], mpl["p"]):
            old_lab = str(jp[jfields.index("edge_num")])
            new_lab = str(mp[mfields.index("edge_num")])
            clade_old = jmap.get(old_lab)
            clade_new = mmap.get(new_lab)
            assert clade_old is not None, "old label %s unknown" % old_lab
            assert clade_new is not None, "new label %s unknown" % new_lab
            assert clade_old == clade_new, (
                "bipartition mismatch: %s -> %s (%r vs %r)"
                % (old_lab, new_lab, sorted(clade_old), sorted(clade_new)))
            n_old += 1
            n_new += 1

    n_jplace = sum(len(p["p"]) for p in jplace["placements"])
    n_merged = sum(len(p["p"]) for p in merged["placements"])
    assert n_jplace == n_merged, "placement count %d != %d" % (
        n_jplace, n_merged)
    assert merged["fields"] == jplace["fields"], "fields mismatch"
    print("VERIFIED %s: %d placements, all edge_num translations "
          "bipartition-consistent" % (merged_path, n_merged))


if __name__ == "__main__":
    main()
