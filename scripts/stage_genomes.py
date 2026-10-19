#!/usr/bin/env python3
"""Stage genome FASTAs for BUSCO: copy *.fasta -> <stem>.fa, with sanity report.

- Verbatim rename: only the extension is swapped; interior dots are preserved.
- Real copies (no symlinks): compute nodes must not dereference /home I/O.
- Report flags nucleotide-like files (colleague warned not all inputs are
  proper protein sets).
"""

import argparse
import shutil
from collections import Counter
from pathlib import Path


def plan_staging(src_dir):
    """Return [(src_path, dst_name)] for every *.fasta in src_dir (sorted).

    Raises ValueError if two files would map to the same .fa name.
    """
    src_dir = Path(src_dir)
    plan = []
    seen = {}
    for f in sorted(src_dir.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        if not f.name.lower().endswith(".fasta"):
            continue
        dst_name = f.name[: -len(".fasta")] + ".fa"
        key = dst_name.lower()
        if key in seen:
            raise ValueError(
                "collision: {} and {} both map to {}".format(seen[key], f.name, dst_name)
            )
        seen[key] = f.name
        plan.append((f, dst_name))
    return plan


def sanity_report(path):
    """Count records/letters and flag nucleotide-like sequence content.

    A/C/G/T are also valid amino-acid letters, so a ratio heuristic cannot
    work; instead a file is suspicious if its observed alphabet is a subset
    of the nucleotide letters {A,C,G,T,N}.
    """
    counts = Counter()
    n_records = 0
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                n_records += 1
                continue
            counts.update(line.strip().upper())
    n_letters = sum(counts.values())
    letters = set(counts) - {"-", "*"}
    suspicious = n_letters > 0 and letters.issubset({"A", "C", "G", "T", "N"})
    return {
        "filename": Path(path).name,
        "n_records": n_records,
        "n_letters": n_letters,
        "suspicious": suspicious,
    }


def write_report(report_path, reports):
    header = ["filename", "n_records", "n_letters", "suspicious"]
    with open(report_path, "w") as fh:
        fh.write("\t".join(header) + "\n")
        for rep in reports:
            fh.write(
                "{}\t{}\t{}\t{}\n".format(
                    rep["filename"], rep["n_records"], rep["n_letters"], rep["suspicious"]
                )
            )


def clean_leading_blank_lines(path):
    """Strip whitespace-only lines BEFORE the first header, in place.

    Biopython's strict 'fasta' parser (used by BUSCO's check_protein_file,
    src/busco/analysis/Analysis.py:124) raises ValueError on files that do
    not start with '>' — and BUSCO converts that into BatchFatalError,
    killing a whole batch chunk. Returns True if the file was modified.
    """
    path = Path(path)
    with open(path) as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines):
        if line.startswith(">"):
            break
        if line.strip():
            return False  # real leading content, do not touch
        if i == len(lines) - 1:  # no header at all
            return False
    else:
        return False
    if i == 0:
        return False
    with open(path, "w") as fh:
        fh.writelines(lines[i:])
    return True


def stage(src_dir, dst_dir, report_path=None, dry_run=False):
    """Copy every *.fasta from src_dir to dst_dir as .fa; return the plan."""
    plan = plan_staging(src_dir)
    if dry_run:
        return plan
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for src_path, dst_name in plan:
        shutil.copy2(src_path, dst_dir / dst_name)
        clean_leading_blank_lines(dst_dir / dst_name)
        reports.append(sanity_report(dst_dir / dst_name))
    if report_path is not None:
        write_report(report_path, reports)
    return plan


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    plan = stage(args.src, args.dst, report_path=args.report, dry_run=args.dry_run)
    if args.dry_run:
        print("planned: {} file(s) (dry run, nothing copied)".format(len(plan)))
    else:
        print("staged: {} file(s) -> {}".format(len(plan), args.dst))
        if args.report is not None:
            print("report: {}".format(args.report))
        print(
            "next:   python3 scripts/make_chunks.py {} <chunks-dir> --chunk-size 8".format(
                args.dst
            )
        )
    for src_path, dst_name in plan[:5]:
        print("  {} -> {}".format(src_path.name, dst_name))
    if len(plan) > 5:
        print("  ...")
    if args.report is not None:
        with open(args.report) as fh:
            next(fh)  # header
            flagged = [line.split("\t")[0] for line in fh if line.rstrip("\n").endswith("True")]
        if flagged:
            print("SUSPICIOUS (nucleotide-like?): {}".format(", ".join(flagged)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
