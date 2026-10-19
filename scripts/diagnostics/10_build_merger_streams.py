#!/usr/bin/env python3
"""Build seppJsonMerger stdin streams from preserved pplacer jplace files.

Reconstructs the stream that sepp's exhaustive.py:271-288 feeds to
`java -jar seppJsonMerger.jar - - <out>` (stdin mode):

    <full labeled tree>;
    <labeled subset tree>;
    <path to .jplace>
    <blank line>

sepp labels edges 0..n-1 in postorder (sepp/tree.py:412) and emits them as
`name:len[label]`. The preserved jplaces only carry pplacer's own `{N}`
labels, so each stream is made self-consistent: the jplace tree is
re-labeled sepp-style and used as BOTH the full-tree line and the subset
line. The merger maps jplace `{N}` -> tree `[N]` labels by bipartition, so
this exercises every fixed code path (regex, field order, mapping, clamp)
without replicating sepp's subset decomposition.

Jplaces whose placements reference the root edge are skipped: the root edge
has no newick token, so neither sepp's real stream nor ours can label it.
"""
import json
import os
import sys

# Offset the synthetic labels away from pplacer's 0-based numbering so the
# merger's bipartition mapping is exercised non-trivially (a plain postorder
# relabeling coincides with pplacer's {N} numbering, making the map identity).
LABEL_OFFSET = int(os.environ.get("SEPP_MERGER_LABEL_OFFSET", "1000"))


class Node:
    def __init__(self):
        self.name = None
        self.length = None
        self.children = []
        self.label = None  # edge label as parsed ({N} or [N])
        self.new_label = None


def parse_newick(s):
    i = 0

    def parse_node():
        nonlocal i
        node = Node()
        if s[i] == "(":
            i += 1
            while True:
                node.children.append(parse_node())
                if s[i] == ",":
                    i += 1
                    continue
                if s[i] == ")":
                    i += 1
                    break
                raise ValueError("bad newick at %d: %r" % (i, s[i - 5:i + 5]))
            # optional internal node name (sepp relabels internal nodes)
            start = i
            while i < len(s) and s[i] not in ":,(){}[":
                i += 1
            if i > start:
                node.name = s[start:i]
        else:
            start = i
            while s[i] not in ":,()":
                i += 1
            node.name = s[start:i]
        if i < len(s) and s[i] == ":":
            i += 1
            start = i
            while s[i] not in ",(){}[]":
                i += 1
            node.length = s[start:i]
        if i < len(s) and s[i] in "{}[":
            close = "}" if s[i] == "{" else "]"
            i += 1
            start = i
            while s[i] != close:
                i += 1
            node.label = s[start:i]
            i += 1
        return node

    root = parse_node()
    return root


def label_edge(node, counter):
    for child in node.children:
        label_edge(child, counter)
    node.new_label = str(counter[0] + LABEL_OFFSET)
    counter[0] += 1


def emit(node):
    parts = []
    if node.children:
        parts.append("(" + ",".join(emit(c) for c in node.children) + ")")
    if node.name:
        parts.append(node.name)
    if node.length is not None:
        parts.append(":" + node.length)
    if node.new_label is not None:
        parts.append("[" + node.new_label + "]")
    return "".join(parts)


def edge_label_map(node, acc):
    if node.label is not None:
        acc[node.label] = node
    for child in node.children:
        edge_label_map(child, acc)
    return acc


def clade(node):
    if not node.children:
        return frozenset([node.name])
    s = set()
    for child in node.children:
        s |= clade(child)
    return frozenset(s)


def build_stream(jplace_path, out_path):
    with open(jplace_path) as fh:
        jplace = json.load(fh)
    root = parse_newick(jplace["tree"])
    counter = [0]
    label_edge(root, counter)
    labels = {}
    edge_label_map(root, labels)

    fields = jplace["fields"]
    ei = fields.index("edge_num")
    root_lab = root.label
    n_pl = 0
    for pl in jplace["placements"]:
        for p in pl["p"]:
            if str(p[ei]) == str(root_lab):
                return None, "placement references root edge"
            n_pl += 1

    tree_line = emit(root)
    stream = "%s;\n%s;\n%s\n\n" % (tree_line, tree_line, jplace_path)
    with open(out_path, "w") as fh:
        fh.write(stream)
    return n_pl, None


def main():
    jplace_dir, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    jplaces = sorted(
        os.path.join(root, p)
        for root, _, files in os.walk(jplace_dir)
        for p in files
        if p.endswith(".jplace")
    )
    if not jplaces:
        sys.exit("no .jplace files under %s" % jplace_dir)
    ok, skipped = [], []
    for jp in jplaces:
        name = os.path.basename(jp).replace(".jplace", "")
        # sanitize: sepp's merge skips nothing; keep names filesystem-safe
        name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
        out = os.path.join(out_dir, name + ".stream")
        n_pl, err = build_stream(jp, out)
        if err:
            skipped.append((jp, err))
        else:
            ok.append((out, jp, n_pl))
    with open(os.path.join(out_dir, "manifest.tsv"), "w") as fh:
        for out, jp, n_pl in ok:
            fh.write("%s\t%s\t%d\n" % (out, jp, n_pl))
    print("streams: %d ok, %d skipped" % (len(ok), len(skipped)))
    for jp, err in skipped:
        print("SKIPPED %s: %s" % (jp, err))


if __name__ == "__main__":
    main()
