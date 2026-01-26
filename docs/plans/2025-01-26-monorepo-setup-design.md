# Aurora DSQL ORM Monorepo Design

**Date:** 2025-01-26
**Status:** Implemented

## Overview

This document describes the design decisions for consolidating Aurora DSQL ORM adapters into a single monorepo.

## Goals

1. Consolidate multiple ORM adapter repositories into one location
2. Support multiple programming languages (Python, TypeScript, Java)
3. Enable independent versioning and releases per adapter
4. Maintain backwards compatibility for existing users
5. Simplify release process for maintainers

## Directory Structure

```
aurora-dsql-orms/
├── python/
│   ├── sqlalchemy/          # aurora-dsql-sqlalchemy package
│   └── tortoise-orm/        # aurora-dsql-tortoise-orm package
├── typescript/              # Future TypeScript adapters
├── java/                    # Future Java adapters
├── .github/
│   └── workflows/           # Consolidated CI/CD workflows
├── docs/
│   └── plans/               # Design documents
└── README.md
```

## Key Decisions

### 1. Multi-Language Monorepo

**Decision:** Top-level directories organized by language.

**Rationale:** Different languages have different build systems, package managers, and release processes. Organizing by language keeps related tooling together.

### 2. Independent Versioning

**Decision:** Each adapter has its own version, released independently.

**Rationale:**
- Adapters are alternatives, not complements (users pick one ORM)
- A bug fix in one adapter shouldn't force version bumps in others
- Different ecosystems have different release cadences

**Tag format:** `python/sqlalchemy/v1.0.0`

### 3. Explicit Version Numbers

**Decision:** Version numbers hardcoded in `pyproject.toml` rather than derived from git tags via `hatch-vcs`.

**Rationale:**
- Simpler to understand and debug
- No magic version derivation
- Works better in monorepo context where tag patterns get complex

### 4. Preserved Package Names

**Decision:** Keep existing PyPI package names (`aurora-dsql-sqlalchemy`, `aurora-dsql-tortoise-orm`).

**Rationale:** Zero migration effort for existing users. `pip install aurora-dsql-sqlalchemy` continues to work unchanged.

### 5. Version Continuity

**Decision:** Continue version numbers from existing PyPI releases.

**Rationale:** Avoid confusion. Users see `1.1.0 → 1.1.1`, not `1.1.0 → 1.0.0`.

Current versions at migration:
- `aurora-dsql-sqlalchemy`: 1.1.0
- `aurora-dsql-tortoise-orm`: 0.1.1

### 6. Git History Preservation

**Decision:** Use `git subtree add` to import existing repositories.

**Rationale:** Preserves commit history, blame, and contributor attribution.

### 7. Consolidated Workflows

**Decision:** All GitHub Actions workflows live at `.github/workflows/` (root level).

**Rationale:**
- Standard monorepo practice
- Easier to maintain and understand
- Shared workflows (cluster create/delete) in one place

## Release Process

1. Update version in `python/<adapter>/pyproject.toml`
2. Commit: `git commit -am "Release <adapter> vX.Y.Z"`
3. Tag: `git tag python/<adapter>/vX.Y.Z`
4. Push: `git push && git push --tags`
5. GitHub Actions automatically publishes to PyPI

## Migration from Old Repos

After this monorepo is live:

1. Update old repo READMEs with "This repo has moved" notice
2. Archive old repos (make read-only)
3. New releases come only from monorepo

## Future Work

- Add TypeScript adapters (Prisma)
- Add Java adapters (Flyway)
- Consider shared documentation site
- Evaluate need for release automation tooling as adapter count grows
