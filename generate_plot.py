#!/usr/bin/env bash
touch .busco 2>/dev/null && rm .busco 2>/dev/null || echo "ERROR User with uid '$(id -u)', cannot write the working directory. Please be sure you mounted a volume and fix the permissions or provide an alternative user using 'docker run -u uid'. See the documentation."
python3.7 /busco/scripts/generate_plot.py $@
