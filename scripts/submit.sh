#!/bin/bash
# submit.sh - the ONLY supported way to submit the sbatch jobs in this repo.
#
# Slurm reads #SBATCH directives as literal text (no variable expansion), so
# per-user paths cannot live in the job headers. This wrapper injects them at
# submission time:
#   --chdir=$BUSCO_WORK --output=$BUSCO_LOGS/%x_%j.log --partition=$BUSCO_PARTITION
# run_busco_array.sbatch instead gets --output=$BUSCO_LOGS/%x_%A_%a.log:
# without %a every array task would write into ONE shared file, interleaving
# the output of the concurrent chunk runs (ticket 008).
# plus --cpus-per-task=$BUSCO_CPUS if BUSCO_CPUS was set in the environment.
# It also stages the workflow files into $BUSCO_WORK/build/ and submits that
# copy, so compute nodes only ever read /work (AGENTS.md).
#
# Usage:
#   submit.sh <job.sbatch> [sbatch options] [script args]
# sbatch options (must start with '-' and precede any script arg, mirroring
# sbatch's own 'options... script args...' semantics):
#   submit.sh scripts/run_busco_array.sbatch --array=0-3 --mem=64G
# script args (first non-option arg onwards, passed to the job script):
#   submit.sh scripts/run_busco.sbatch /work/$USER/busco/all_seqs/GENOME.fa
#
# Later options win in sbatch, so anything passed here overrides the injected
# defaults.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
export BUSCO_LIB="$SCRIPT_DIR/lib.sh"

# Record whether the caller set BUSCO_CPUS before lib.sh applies its default.
CPUS_WAS_SET=${BUSCO_CPUS+x}

# shellcheck source=lib.sh
. "$BUSCO_LIB"

usage() {
    echo "usage: $0 <job.sbatch> [sbatch options/script args...]" >&2
    echo "jobs: build_sif.sbatch, run_busco.sbatch, run_busco_array.sbatch" >&2
    exit 1
}

JOB=${1:-}
[ -n "$JOB" ] || usage
shift
JOB_SRC=$SCRIPT_DIR/$(basename "$JOB")
[ -f "$JOB_SRC" ] || { echo "ERROR: no such job script: $JOB_SRC" >&2; exit 1; }
case "$(basename "$JOB")" in
    build_sif.sbatch|run_busco.sbatch|run_busco_array.sbatch) ;;
    *) usage ;;
esac

# Stage the workflow into $BUSCO_WORK/build: lib.sh + job scripts are sourced
# at runtime on the compute node, so they must live on /work. busco.def, the
# BuscoPlacer patch and the vendored pplacer binaries are needed by the build
# (built with cwd=$BUSCO_WORK/build so the %files relative paths resolve).
mkdir -p "$BUSCO_WORK/build/scripts/patches" "$BUSCO_WORK/build/pplacer_bin" "$BUSCO_LOGS"
for f in lib.sh build_sif.sh build_sif.sbatch run_busco.sbatch \
        run_busco_array.sbatch; do
    cp -p "$SCRIPT_DIR/$f" "$BUSCO_WORK/build/$f"
done
cp -p "$SCRIPT_DIR/../busco.def" "$BUSCO_WORK/build/busco.def"
cp -p "$SCRIPT_DIR/patches/BuscoPlacer.py" \
    "$BUSCO_WORK/build/scripts/patches/BuscoPlacer.py"
cp -p "$SCRIPT_DIR/../pplacer_bin/pplacer" "$SCRIPT_DIR/../pplacer_bin/guppy" \
    "$SCRIPT_DIR/../pplacer_bin/rppr" "$BUSCO_WORK/build/pplacer_bin/"

export BUSCO_REPO_ROOT=$BUSCO_WORK/build
JOB_ABS=$BUSCO_WORK/build/$(basename "$JOB")

# Split user args: leading options (start with '-') are sbatch options and
# must come BEFORE the job path - everything after the script path would be
# treated as script args by sbatch and silently NOT applied (seen live:
# --array=0 after the job path ran the job as a plain job). The first
# non-option arg starts the script args (e.g. the input FASTA for
# run_busco.sbatch), which must stay after the job path.
SBATCH_ARGS=()
SCRIPT_ARGS=()
in_script_args=0
for arg in "$@"; do
    if [ "$in_script_args" = 1 ] || [[ "$arg" != -* ]]; then
        in_script_args=1
        SCRIPT_ARGS+=("$arg")
    else
        SBATCH_ARGS+=("$arg")
    fi
done

# Fail fast on the login node (ticket 007): the README placeholder "MY.fa"
# was submitted literally and the job failed in 1 s with the error only in
# the SLURM log. run_busco.sbatch input is validated here so a bad path
# never reaches sbatch. The job runs with --chdir=$BUSCO_WORK, hence the
# absolute-path requirement.
if [ "$(basename "$JOB")" = "run_busco.sbatch" ]; then
    if [ "${#SCRIPT_ARGS[@]}" -eq 0 ]; then
        echo "ERROR: run_busco.sbatch needs an input FASTA argument" >&2
        echo "usage: $0 scripts/run_busco.sbatch $BUSCO_SEQ/<genome>.fa" >&2
        exit 1
    fi
    INPUT=${SCRIPT_ARGS[0]}
    case "$INPUT" in
        /*) ;;
        *)
            echo "ERROR: input path must be absolute (the job chdirs to" >&2
            echo "$BUSCO_WORK on the compute node): '$INPUT'" >&2
            exit 1
            ;;
    esac
    if [ ! -f "$INPUT" ]; then
        echo "ERROR: input FASTA not found: '$INPUT'" >&2
        echo "Not the literal README placeholder? Use one of your staged genomes:" >&2
        echo "  ls $BUSCO_SEQ" >&2
        n=$(find "$BUSCO_SEQ" -maxdepth 1 -type f -name '*.fa' 2>/dev/null | wc -l)
        if [ "$n" -gt 0 ]; then
            echo "staged .fa files under $BUSCO_SEQ: $n, e.g.:" >&2
            find "$BUSCO_SEQ" -maxdepth 1 -type f -name '*.fa' | sort | head -3 | \
                while read -r f; do echo "  $f" >&2; done
        fi
        exit 1
    fi
    case "$INPUT" in
        *.fa) ;;
        *)
            echo "WARNING: input suffix is not .fa (sepp munges the literal" >&2
            echo "string 'fasta' in paths, BUSCO #432/#781); stage inputs as" >&2
            echo ".fa via scripts/stage_genomes.py" >&2
            ;;
    esac
fi

# Log pattern per job type: single jobs share %x_%j.log; array jobs need
# %a (task id), otherwise every task writes into ONE shared file,
# interleaving the output of the concurrent chunk runs (ticket 008).
# %A = array master jobid, %a = task id -> one log per array task.
OUT_PATTERN='%x_%j.log'
if [ "$(basename "$JOB")" = "run_busco_array.sbatch" ]; then
    OUT_PATTERN='%x_%A_%a.log'
fi

INJECT=(
    --chdir="$BUSCO_WORK"
    --output="$BUSCO_LOGS/$OUT_PATTERN"
    --partition="$BUSCO_PARTITION"
)
if [ -n "$CPUS_WAS_SET" ]; then
    INJECT+=(--cpus-per-task="$BUSCO_CPUS")
fi

EXTRA=()
if [ "$(basename "$JOB")" = "run_busco_array.sbatch" ]; then
    # Chunk dirs are required for EVERY array submission (auto range or
    # explicit --array): without them every task dies on the node. Ticket
    # 014: the old count pipeline `n=$(find ... | wc -l)` killed this
    # script SILENTLY under set -euo pipefail when $BUSCO_CHUNKS did not
    # exist (find fails -> substitution status 1 -> set -e), so the error
    # never surfaced and nothing was submitted. The `|| true` inside the
    # braces plus the -d pre-check make the count pipefail-proof.
    n=0
    if [ -d "$BUSCO_CHUNKS" ]; then
        n=$({ find "$BUSCO_CHUNKS" -maxdepth 1 -type d -name 'chunk_*' 2>/dev/null || true; } | wc -l)
    fi
    if [ "$n" -eq 0 ]; then
        echo "ERROR: no chunk_* dirs under $BUSCO_CHUNKS - refusing to submit" >&2
        echo "       (a plain submission would die on the node: SLURM_ARRAY_TASK_ID unset)." >&2
        echo "       Stage and chunk first, then resubmit:" >&2
        echo "         python3 scripts/stage_genomes.py \"\$BUSCO_INPUT_DIR\" $BUSCO_SEQ \\" >&2
        echo "             --report $BUSCO_WORK/stage_report.tsv" >&2
        echo "         python3 scripts/make_chunks.py $BUSCO_SEQ $BUSCO_CHUNKS --chunk-size 8" >&2
        exit 1
    fi
    want_array=1
    for arg in "${SBATCH_ARGS[@]}" "${SCRIPT_ARGS[@]}"; do
        case "$arg" in --array=*) want_array=0 ;; esac
    done
    if [ "$want_array" = 1 ]; then
        range="0-$((n - 1))"
        [ -n "$BUSCO_ARRAY_LIMIT" ] && range="$range%$BUSCO_ARRAY_LIMIT"
        EXTRA+=(--array="$range")
    fi
fi

exec sbatch "${INJECT[@]}" "${EXTRA[@]}" "${SBATCH_ARGS[@]}" "$JOB_ABS" "${SCRIPT_ARGS[@]}"
