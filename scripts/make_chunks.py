#!/usr/bin/env python3
"""Split staged genome names into deterministic chunk dirs for a SLURM array.

BUSCO batch mode (`-i dir`) is strictly sequential inside one job
(src/busco/BuscoRunner.py:284), so cross-genome parallelism comes entirely
from the array: each chunk dir feeds one array task.
"""

import argparse
import shutil
from pathlib import Path


def chunk_names(names, chunk_size):
    """Split an iterable of names into sorted chunks of chunk_size.

    Deterministic: names are sorted first; the last chunk may be smaller.
    """
    if chunk_size < 1:
        raise ValueError("chunk size must be >= 1")
    ordered = sorted(names)
    if not ordered:
        raise ValueError("empty input list")
    return [ordered[i : i + chunk_size] for i in range(0, len(ordered), chunk_size)]


def make_chunks(src_dir, out_dir, chunk_size):
    """Copy staged *.fa files from src_dir into out_dir/chunk_NN dirs.

    Returns the chunk plan: [(chunk_dir_name, [names])].
    """
    src_dir = Path(src_dir)
    out_dir = Path(out_dir)
    names = [f.name for f in sorted(src_dir.iterdir()) if f.is_file() and f.name.endswith(".fa")]
    plan = chunk_names(names, chunk_size)
    for i, chunk in enumerate(plan):
        cdir = out_dir / "chunk_{:02d}".format(i)
        cdir.mkdir(parents=True, exist_ok=True)
        for name in chunk:
            shutil.copy2(src_dir / name, cdir / name)
    return [("chunk_{:02d}".format(i), c) for i, c in enumerate(plan)]


def write_manifest(out_dir, plan):
    with open(Path(out_dir) / "manifest.tsv", "w") as fh:
        fh.write("chunk\tgenome\n")
        for cname, names in plan:
            for name in names:
                fh.write("{}\t{}\n".format(cname, name))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path, help="dir with staged *.fa files")
    ap.add_argument("out", type=Path, help="dir to create chunk_NN dirs in")
    ap.add_argument("--chunk-size", type=int, default=8)
    args = ap.parse_args(argv)

    if not args.src.is_dir():
        ap.error(
            "source dir not found: {} (stage first: "
            "python3 scripts/stage_genomes.py <input-dir> {})".format(args.src, args.src)
        )
    plan = make_chunks(args.src, args.out, args.chunk_size)
    write_manifest(args.out, plan)
    print("chunks: {} x <= {} file(s)".format(len(plan), args.chunk_size))
    for cname, names in plan:
        print("  {}: {}..{}".format(cname, names[0], names[-1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
