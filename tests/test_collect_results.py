from collect_results import _genome_name, add_failures, collect, parse_summary

SUMMARY = """# BUSCO version is: 6.1.0
# The lineage dataset is: eukaryota_odb12.2
# BUSCO was run in mode: proteins
***** Results from dataset eukaryota_odb12.2 *****

C:86.4%[S:76.0%,D:10.4%],F:3.2%,M:10.4%,n:125
"""


def test_genome_name_with_dotted_lineage():
    assert (
        _genome_name("short_summary.specific.eukaryota_odb12.2.G1.fa.txt") == "G1"
    )


def test_genome_name_keeps_interior_dots():
    assert (
        _genome_name(
            "short_summary.specific.eukaryota_odb12.2.Beta_vulgaris_subsp._vulgaris_combined.fa.txt"
        )
        == "Beta_vulgaris_subsp._vulgaris_combined"
    )


def test_parse_summary_extracts_percentages():
    row = parse_summary(SUMMARY)
    assert row == {
        "complete_pct": 86.4,
        "single_pct": 76.0,
        "duplicated_pct": 10.4,
        "fragmented_pct": 3.2,
        "missing_pct": 10.4,
        "n_markers": 125,
    }


def test_parse_summary_returns_none_without_results(tmp_path):
    assert parse_summary("no results here\n") is None


def test_collect_walks_both_result_layouts(tmp_path):
    old = tmp_path / "chunk_00" / "BUSCO_res" / "G1.fa"
    old.mkdir(parents=True)
    (old / "short_summary.specific.eukaryota_odb12.2.G1.fa.txt").write_text(SUMMARY)
    new = tmp_path / "chunk_05" / "G2.fa"
    new.mkdir(parents=True)
    (new / "short_summary.specific.eukaryota_odb12.2.G2.txt").write_text(SUMMARY)
    rows = collect(tmp_path)
    assert sorted(r["genome"] for r in rows) == ["G1", "G2"]
    assert rows[0]["flag"] == "ok"


def test_collect_flags_all_missing(tmp_path):
    empty = tmp_path / "chunk_00" / "G3.fa"
    empty.mkdir(parents=True)
    txt = SUMMARY.replace("C:86.4%[S:76.0%,D:10.4%],F:3.2%,M:10.4%,n:125",
                          "C:0.0%[S:0.0%,D:0.0%],F:0.0%,M:100.0%,n:125")
    (empty / "short_summary.specific.eukaryota_odb12.2.G3.txt").write_text(txt)
    rows = collect(tmp_path)
    assert rows[0]["flag"] == "EMPTY"


def test_add_failures_appends_rows(tmp_path):
    failed = tmp_path / "failed.txt"
    failed.write_text("# duplicate IDs\nG7\nG8\n")
    rows = add_failures([], failed)
    assert [r["genome"] for r in rows] == ["G7", "G8"]
    assert all(r["flag"] == "FAILED" for r in rows)
    assert rows[0]["complete_pct"] == ""


def test_add_failures_skips_already_present(tmp_path):
    failed = tmp_path / "failed.txt"
    failed.write_text("G1\n")
    rows = add_failures([{"genome": "G1", "flag": "ok"}], failed)
    assert len(rows) == 1
