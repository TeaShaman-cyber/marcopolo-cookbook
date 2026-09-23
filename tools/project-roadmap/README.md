# MarcoPolo roadmap verifier

Read-only GitHub Project verifier for cookbook lifecycle coordination.

Normal live check:

```bash
tools/project-roadmap/check --snapshot-output /tmp/marcopolo-roadmap.json --receipt /tmp/marcopolo-roadmap-receipt.json
```

The verifier compares two independent Project views:

1. `ProjectV2.items` (project-centric connection), and
2. repository Issue/PR `projectItems` reverse membership.

It reports `PASS`, `DRIFT`, or `UNAVAILABLE`. `DRIFT` is evidence to inspect; it
is not mutation authority. The tool never changes Issue, PR, or Project state.

The normalized snapshot omits Issue/PR body text. It stores stable entity identity
`(repository, entity_type, number)`, lifecycle markers derived from explicit body
markers, Project item identity, and single-select coordination fields.

Supported explicit body markers are:

```text
Parent: #48
Disposition: MIGRATED
Migration-Receipt: https://github.com/...
Owner-Issue: #123
```

`Refs #123`, `Fixes #123`, and `Closes #123` are also recognized as PR ownership
markers. Migration receipt checks activate only when `Disposition: MIGRATED` is
explicitly present.

Network/GitHub verification remains separate from `tools/dev/check`; local tests
and frozen fixtures for this verifier run under the normal repository QA gate.
