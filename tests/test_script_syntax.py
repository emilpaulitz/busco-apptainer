"""Every shell/sbatch script in scripts/ (recursively) must parse with bash -n."""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = sorted((REPO / "scripts").rglob("*"))
SCRIPTS = [p for p in SCRIPTS if p.is_file() and p.suffix in {".sh", ".sbatch"}]


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: str(p.relative_to(REPO)))
def test_bash_syntax(path):
    result = subprocess.run(
        ["bash", "-n", str(path)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"bash -n failed for {path}:\n{result.stderr}"
