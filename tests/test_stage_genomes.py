import subprocess
import sys
from pathlib import Path

import pytest

from stage_genomes import clean_leading_blank_lines, plan_staging, sanity_report, stage

REPO = Path(__file__).resolve().parents[1]


def _cli(*args):
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "stage_genomes.py"), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def src(tmp_path):
    d = tmp_path / "src"
    d.mkdir()
    return d


def test_plan_maps_fasta_to_fa_verbatim(src):
    (src / "Beta_vulgaris_subsp._vulgaris_combined.fasta").touch()
    plan = plan_staging(src)
    assert plan == [
        (src / "Beta_vulgaris_subsp._vulgaris_combined.fasta",
         "Beta_vulgaris_subsp._vulgaris_combined.fa")
    ]


def test_plan_ignores_non_fasta(src):
    (src / "notes.txt").touch()
    (src / "genome.fa").touch()
    (src / "hidden.fasta").touch()
    (src / ".secret.fasta").touch()
    assert plan_staging(src) == [(src / "hidden.fasta", "hidden.fa")]


def test_plan_rejects_stem_collisions(src):
    (src / "A.fasta").touch()
    (src / "A.FASTA").touch()
    with pytest.raises(ValueError, match="collision"):
        plan_staging(src)


def test_sanity_counts_records_and_accepts_protein(tmp_path):
    p = tmp_path / "prot.fa"
    p.write_text(">s1\nMAGKTSLVIA\n>s2\nMFVKQ*\n")
    rep = sanity_report(p)
    assert rep["n_records"] == 2
    assert rep["suspicious"] is False


def test_sanity_flags_nucleotide_like(tmp_path):
    p = tmp_path / "nucl.fa"
    p.write_text(">s1\nACGTACGTAC\n>s2\nTTGACCAAGN\n")
    rep = sanity_report(p)
    assert rep["n_records"] == 2
    assert rep["suspicious"] is True


def test_stage_copies_renamed_and_writes_report(src, tmp_path):
    (src / "G1.fasta").write_text(">s1\nMAGKTSLVIA\n")
    dst = tmp_path / "dst"
    plan = stage(src, dst, report_path=tmp_path / "report.tsv")
    staged = dst / "G1.fa"
    assert staged.read_text() == ">s1\nMAGKTSLVIA\n"
    lines = (tmp_path / "report.tsv").read_text().splitlines()
    assert lines[0].split("\t") == ["filename", "n_records", "n_letters", "suspicious"]
    assert len(lines) == 2
    assert plan == [(src / "G1.fasta", "G1.fa")]


def test_stage_dry_run_copies_nothing(src, tmp_path):
    (src / "G1.fasta").write_text(">s1\nMAGKTSLVIA\n")
    dst = tmp_path / "dst"
    stage(src, dst, dry_run=True)
    assert not dst.exists()


def test_clean_strips_leading_blank_lines(tmp_path):
    p = tmp_path / "g.fa"
    p.write_text("\n\n\n>s1\nMAGKTSLVIA\n")
    assert clean_leading_blank_lines(p) is True
    assert p.read_text() == ">s1\nMAGKTSLVIA\n"


def test_clean_keeps_clean_file(tmp_path):
    p = tmp_path / "g.fa"
    p.write_text(">s1\nMAGKTSLVIA\n")
    assert clean_leading_blank_lines(p) is False
    assert p.read_text() == ">s1\nMAGKTSLVIA\n"


def test_stage_cleans_leading_blank_lines(src, tmp_path):
    (src / "G1.fasta").write_text("\n\n>s1\nMAGKTSLVIA\n")
    dst = tmp_path / "dst"
    stage(src, dst)
    assert (dst / "G1.fa").read_text() == ">s1\nMAGKTSLVIA\n"


def test_cli_real_run_says_staged_with_report_and_next_hint(tmp_path):
    # ticket 014: a real copy printed "planned: N file(s)" - identical to a
    # dry run, no report path, no next step. Output must state what happened.
    src = tmp_path / "src"
    src.mkdir()
    (src / "G1.fasta").write_text(">s1\nMAGKTSLVIA\n")
    dst = tmp_path / "dst"
    report = tmp_path / "report.tsv"
    r = _cli(str(src), str(dst), "--report", str(report))
    assert r.returncode == 0, r.stderr
    assert "staged: 1 file(s)" in r.stdout
    assert str(dst) in r.stdout
    assert str(report) in r.stdout
    assert "make_chunks" in r.stdout
    assert "planned:" not in r.stdout


def test_cli_dry_run_keeps_planned_wording(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "G1.fasta").touch()
    r = _cli(str(src), str(tmp_path / "dst"), "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "planned: 1 file(s)" in r.stdout
