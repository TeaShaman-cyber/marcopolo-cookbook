# Changelog

All notable changes to the MarcoPolo Cookbook are recorded here.

This repository follows Semantic Versioning. While the project remains below
`1.0.0`, releases are operational/pre-stable snapshots: they identify a reviewed
and reproducible state, but they do not imply that every research line, lifecycle
cleanup item, or upstream dependency issue is complete.

## [Unreleased]

No committed release-scope changes yet.

## [0.1.0] - 2026-09-23

First public operational release of the cookbook as a reproducible MarcoPolo / Theseus engineering surface.

### Added

- Git-backed workspace `RULES.md` projection and project-contract/change-control guidance for routing, authority, currentness, permissions, persistence, and exact readback.
- Canonical local QA entrypoint, `tools/dev/check`, plus NFS-friendly development tooling and reusable verification-ladder CI profiles.
- Reusable hosted witness profiles for workflow security, dependency security, property-based checks, and bounded mutation testing.
- Governed GitHub/Git credential routing, explicit Projects V2 capability checks, worktree-currentness verification, and lifecycle policy separating QA, verification, acceptance, merge, release, and migration.
- Session Search operational tooling for cumulative historical evidence, acceptance/rebuild verification, implementation/corpus freshness status, and runtime helper materialization.
- Freshness-bound local Session Search read projection for interactive queries. Durable corpus evidence remains authoritative; cache failure degrades explicitly to the durable route.
- Small review methods (Feynman checkpoint and Five Whys), MCP/mcporter/MCPJam operational workbenches, cloud-reference evidence, and bounded forum/client routing notes.

### Changed

- Session Search normal interactive routing is now one bounded command with fail-closed local implementation/corpus checks instead of workspace archaeology.
- Broad NFS-backed Session Search queries can use a validated disposable local SQLite projection, reducing representative warm broad/scoped/recall latency from multi-second NFS paths to sub-second local paths while preserving byte-identical search output in acceptance probes.
- GitHub capability routing now distinguishes repository reads, governed writes, Projects V2 access, and Git smart-HTTP rather than treating all GitHub access as one capability.
- Repository lifecycle rules now require explicit terminal disposition and exact readback so merged work does not remain indefinitely as draft/active-looking state.

### Verification snapshot

Immediately before release preparation, merged `main` passed:

- 80/80 repository tests;
- 31/31 Session Search helper/integration tests;
- `DEV_CHECK_PASS` through `tools/dev/check`;
- workflow-security on the accepted Session Search release candidates.

Release verification is scoped evidence for this repository state; it is not scientific acceptance for Theseus research lines.

### Known issues and backlog

The release intentionally does **not** hide known debt:

- Dependency-security remains non-green because the current MCPJam CLI lock resolves transitive `undici 5.29.0`; 12 OSV/GitHub Security Advisories are tracked in #96 and #79. The first release does not classify this as PASS.
- Lifecycle cleanup remains active under #48, with explicit work in #49, #50, #51, and #54 to disposition stale/completed work, rehome cross-domain research, archive old implementation PRs, and verify Project graph state.
- Workspace/worktree hygiene remains active in #71.
- Reusable witness/verification infrastructure continues in #64, #72, and #89.
- Credential, routing, runtime, and research questions remain visible in Project #8 rather than being closed for release cosmetics.
- During release-roadmap synchronization, direct Project item reads verified newly added items and field values, while the Project item-list connection temporarily continued to report the earlier item count. This readback inconsistency is recorded under #54; release notes do not treat Project listing consistency as proven until that surface converges.

The living coordination backlog is Project #8, **Theseus — MarcoPolo Operations**. Project state is a coordination projection; Git, Issues, accepted QA, and exact readback remain authority.
