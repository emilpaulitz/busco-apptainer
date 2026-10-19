#!/bin/bash
# build_sif.sh - Build the fully-fixed BUSCO Apptainer SIF
# (quay.io busco 6.1.0 + standalone pplacer + sepp 4.5.6 merger jar +
# BuscoPlacer.py edge_num patch, tickets 003/006).
set -euo pipefail

LIB="${BUSCO_LIB:-$(dirname "$(readlink -f "$0")")/lib.sh}"
# shellcheck source=lib.sh
. "$LIB"

export https_proxy=${https_proxy:-$BUSCO_PROXY}
export http_proxy=${http_proxy:-$https_proxy}

DEF=$BUSCO_REPO_ROOT/busco.def
SIF=$BUSCO_SIF
mkdir -p "$BUSCO_WORK"

action=${1:-}
if [ -f "$SIF" ] && [ "$action" != "rebuild" ]; then
    echo "SIF already exists: $SIF"
    echo "Re-run with 'rebuild' to build from the current busco.def."
    exit 0
fi

# Ensure that the old SIF is not deleted before the new one was built successfully.
TMP_SIF=$(mktemp --suffix=.sif /tmp/busco_build.XXXXXX)
trap 'rm -f "$TMP_SIF"' EXIT

# The %files source in busco.def resolves relative to the CWD of
# `apptainer build`; run from BUSCO_REPO_ROOT so it works both from the repo
# and from the /work-staged build dir that submit.sh prepares.
cd "$BUSCO_REPO_ROOT"

if apptainer build --force --fakeroot "$TMP_SIF" "$DEF"; then
    mv "$TMP_SIF" "$SIF"
    echo "OK: $SIF"
else
    echo "FAILED. If the error mentions missing subuid/subgid entries,"
    echo "this must be fixed by an admin (e.g. /etc/subuid + setuid helper)."
    echo "No sudo workaround is attempted. The previous SIF (if any) is untouched."
    exit 1
fi
