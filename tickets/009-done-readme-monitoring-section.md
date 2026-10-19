# 009 - README: dedicated Monitoring section

## Problem

Monitoring guidance (squeue, log locations, sacct) was buried in inline
comments inside the TL;DR block, and the "Layout on /work" table only knew
`%x_%j.log`. With ticket 008's per-task array logs the inline comments
became both wrong and redundant.

## Change

- New section "Monitoring jobs and logs" (after TL;DR): `squeue`,
  `sacct -j <jobid> --format=State,ExitCode,Elapsed`, example `less` calls
  for single jobs (`busco_<jobid>.log`) and array tasks
  (`busco_array_<master>_<task>.log`), plus three bullets: where the log
  names come from (injected `--output` patterns), the left-squeue-may-have-
  failed rule, and the `/dev/tty` progress-bar caveat.
- TL;DR: removed the inline monitoring comment block and the squeue aside;
  left one-line pointers to the new section.
- "Layout on /work": `logs/` comment now shows both patterns.

## Hurdles

None - tests (`test_no_hardcoded_paths.py`) already scan README.md; all 66
pass.
