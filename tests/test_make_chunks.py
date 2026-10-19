import subprocess
import sys
from pathlib import Path

import pytest

from make_chunks import chunk_names

REPO = Path(__file__).resolve().parents[1]


def make_names(n):
    return [f"G{i:03d}.fa" for i in range(n)]


def test_88_names_make_11_chunks_of_8():
    chunks = chunk_names(make_names(88), 8)
    assert len(chunks) == 11
    assert all(len(c) == 8 for c in chunks)


def test_chunks_preserve_sorted_order():
    chunks = chunk_names(sorted(make_names(20), reverse=True), 8)
    flat = [x for c in chunks for x in c]
    assert flat == sorted(make_names(20))


def test_uneven_last_chunk_is_smaller():
    chunks = chunk_names(make_names(10), 8)
    assert [len(c) for c in chunks] == [8, 2]


def test_no_name_lost_or_duplicated():
    chunks = chunk_names(make_names(88), 8)
    flat = [x for c in chunks for x in c]
    assert sorted(flat) == sorted(make_names(88))


def test_deterministic():
    assert chunk_names(make_names(88), 8) == chunk_names(make_names(88), 8)


def test_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        chunk_names([], 8)


def test_rejects_bad_chunk_size():
    with pytest.raises(ValueError, match="chunk size"):
        chunk_names(make_names(5), 0)


def test_cli_missing_src_dir_fails_with_guidance(tmp_path):
    # ticket 014: a nonexistent source dir raised a raw FileNotFoundError
    # traceback; must instead print a clean error pointing at staging.
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "make_chunks.py"),
            str(tmp_path / "nope"),
            str(tmp_path / "chunks"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode != 0
    assert "source dir not found" in r.stderr
    assert "stage_genomes" in r.stderr
    assert "Traceback" not in r.stderr
    assert "Traceback" not in r.stdout
