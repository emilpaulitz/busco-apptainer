#!/usr/bin/env python3
"""Collect per-genome BUSCO short summaries into one TSV.

Walks results/ recursively, so both result layouts produced in ticket 002
(batch mode: chunk_NN/BUSCO_res/<genome>.fa/ and per-genome mode:
chunk_NN/<genome>/) are picked up. Genomes with 0% complete are flagged
EMPTY (colleague's warning: "not all will give meaningful results").
"""

import argparse
import re
from pathlib import Path

SUMMARY_RE = re.compile(
    r"C:(?P<c>[\d.]+)%\[S:(?P<s>[\d.]+)%,D:(?P<d>[\d.]+)%\],"
    r"F:(?P<f>[\d.]+)%,M:(?P<m>[\d.]+)%,n:(?P<n>\d+)"
)

HEADER = [
    "genome",
    "chunk",
    "complete_pct",
    "single_pct",
    "duplicated_pct",
    "fragmented_pct",
    "missing_pct",
    "n_markers",
    "flag",
]


def parse_summary(text):
    m = SUMMARY_RE.search(text)
    if m is None:
        return None
    return {
        "complete_pct": float(m.group("c")),
        "single_pct": float(m.group("s")),
        "duplicated_pct": float(m.group("d")),
        "fragmented_pct": float(m.group("f")),
        "missing_pct": float(m.group("m")),
        "n_markers": int(m.group("n")),
    }


def _genome_name(path):
    # short_summary.specific.<lineage>.<genome>.txt  OR  ...<genome>.fa.txt
    # <lineage> may contain a dot (eukaryota_odb12.2): drop it via its
    # numeric second component, keep the genome's interior dots intact.
    name = Path(path).name
    name = re.sub(r"\.txt$", "", name)
    name = re.sub(r"^short_summary\.specific\.", "", name)
    parts = name.split(".")
    if len(parts) > 1 and parts[1].isdigit():
        parts = parts[2:]
    else:
        parts = parts[1:]
    return ".".join(parts).removesuffix(".fa")


def collect(results_dir):
    rows = []
    for f in sorted(Path(results_dir).rglob("short_summary.specific.*.txt")):
        parsed = parse_summary(f.read_text())
        if parsed is None:
            continue
        chunk = f.relative_to(results_dir).parts[0] if len(f.relative_to(results_dir).parts) > 1 else ""
        rows.append({
            "genome": _genome_name(f),
            "chunk": chunk,
            **parsed,
            "flag": "EMPTY" if parsed["complete_pct"] == 0.0 else "ok",
        })
    return rows


def add_failures(rows, failed_path):
    """Append FAILED rows for genomes listed in failed_path ('#'-comments ok).

    Genomes that produced a summary anyway (should not happen) are skipped.
    """
    known = {r["genome"] for r in rows}
    out = list(rows)
    with open(failed_path) as fh:
        for line in fh:
            name = line.split("#")[0].strip()
            if not name or name in known:
                continue
            out.append({
                "genome": name,
                "chunk": "",
                "complete_pct": "",
                "single_pct": "",
                "duplicated_pct": "",
                "fragmented_pct": "",
                "missing_pct": "",
                "n_markers": "",
                "flag": "FAILED",
            })
    return out


def write_tsv(path, rows):
    with open(path, "w") as fh:
        fh.write("\t".join(HEADER) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[h]) for h in HEADER) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", type=Path)
    ap.add_argument("--out", type=Path, default=Path("busco_summary.tsv"))
    ap.add_argument("--failed", type=Path, default=None,
                    help="text file with genome names that produced no run "
                         "(one per line, '#'-comments allowed); added as "
                         "flag=FAILED rows")
    args = ap.parse_args(argv)

    rows = collect(args.results)
    if args.failed is not None:
        rows = add_failures(rows, args.failed)
    write_tsv(args.out, rows)
    empty = [r["genome"] for r in rows if r["flag"] == "EMPTY"]
    print("collected: {} genome(s)".format(len(rows)))
    print("EMPTY (0% complete): {}".format(len(empty)))
    for g in empty:
        print("  {}".format(g))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
