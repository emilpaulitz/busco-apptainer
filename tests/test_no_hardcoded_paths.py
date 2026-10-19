"""RED-guard: no user-specific paths in the supported workflow files.

The supported set is scripts/*.sh, scripts/*.sbatch, scripts/*.py,
scripts/*.def (top level only), plus busco.def and README.md at the repo
root. Explicitly out of scope: scripts/diagnostics/ and scripts/fallback/
(historical evidence, see their READMEs) and tickets/ (contain the original
neumann19-era paths as documentation).
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

FORBIDDEN = ("/work/neumann19", "/home/neumann19")

SCRIPT_SUFFIXES = {".sh", ".sbatch", ".py", ".def"}

SUPPORTED_FILES = sorted(
    [
        p
        for p in (REPO / "scripts").iterdir()
        if p.is_file() and p.suffix in SCRIPT_SUFFIXES
    ]
    + [REPO / "busco.def", REPO / "README.md"]
)


@pytest.mark.parametrize("path", SUPPORTED_FILES, ids=lambda p: str(p.relative_to(REPO)))
def test_no_hardcoded_user_paths(path):
    assert path.is_file(), f"missing supported file: {path}"
    for lineno, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        for needle in FORBIDDEN:
            assert needle not in line, (
                f"{path.relative_to(REPO)}:{lineno} contains hardcoded "
                f"'{needle}': {line.strip()}"
            )
