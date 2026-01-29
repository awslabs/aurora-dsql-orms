<a id="python/sqlalchemy/v1.1.2"></a>
# [Aurora DSQL dialect for SQLAlchemy v1.1.2 (python/sqlalchemy/v1.1.2)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/sqlalchemy/v1.1.2) - 2026-01-29

This release updates the documentation to reference the new [aurora-dsql-orms](https://github.com/awslabs/aurora-dsql-orms) monorepo. There should be no functional change to the adapter.

## What's Changed
* Update repo links pointing to old repo by [@danielfrankcom](https://github.com/danielfrankcom) in [#4](https://github.com/awslabs/aurora-dsql-orms/pull/4)
* Merge dev tooling from subprojects at root level by [@danielfrankcom](https://github.com/danielfrankcom) in [#13](https://github.com/awslabs/aurora-dsql-orms/pull/13)
* Standardize workflow permissions by [@danielfrankcom](https://github.com/danielfrankcom) in [#16](https://github.com/awslabs/aurora-dsql-orms/pull/16)
* Consolidate .gitignore files by [@danielfrankcom](https://github.com/danielfrankcom) in [#17](https://github.com/awslabs/aurora-dsql-orms/pull/17)
* Wait for CI before releasing by [@danielfrankcom](https://github.com/danielfrankcom) in [#21](https://github.com/awslabs/aurora-dsql-orms/pull/21)
* Update changelog files as part of release by [@danielfrankcom](https://github.com/danielfrankcom) in [#20](https://github.com/awslabs/aurora-dsql-orms/pull/20)
* Consolidate docs/licensing by [@danielfrankcom](https://github.com/danielfrankcom) in [#18](https://github.com/awslabs/aurora-dsql-orms/pull/18)
* Bump ruff from 0.14.13 to 0.14.14 in /python/sqlalchemy by [@dependabot](https://github.com/dependabot)[bot] in [#54](https://github.com/awslabs/aurora-dsql-orms/pull/54)
* Bump sqlalchemy from 2.0.45 to 2.0.46 in /python/sqlalchemy by [@dependabot](https://github.com/dependabot)[bot] in [#50](https://github.com/awslabs/aurora-dsql-orms/pull/50)

**Full Changelog**: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.1.1...python/sqlalchemy/v1.1.2

[Changes][python/sqlalchemy/v1.1.2]


<a id="python/sqlalchemy/v1.1.1"></a>
# [Aurora DSQL dialect for SQLAlchemy v1.1.1 (python/sqlalchemy/v1.1.1)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/sqlalchemy/v1.1.1) - 2026-01-29

This release migrates the SQLAlchemy adapter to the new [Aurora DSQL ORM Adapters monorepo](https://github.com/awslabs/aurora-dsql-orms), improves SSL/TLS
configuration defaults, and adds type checking support.

The sslrootcert parameter now defaults to `"system"` instead of `"./root.pem"`, using the system's default certificate authority trust store. On systems where the Amazon Root CA is already trusted, no additional SSL configuration is required. See the new [SSL/TLS Configuration documentation](https://github.com/awslabs/aurora-dsql-orms/blob/python/sqlalchemy/v1.1.1/python/sqlalchemy/docs/SSL_CONFIGURATION.md) for details.

The codebase now passes pyright strict type checking. Example code has been modernized to use SQLAlchemy 2.0 `Mapped[]` and `mapped_column()` style for proper type inference.

## What's Changed
* Fix pyright errors by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#42](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/42)
* Fix formatting/linter issues by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#43](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/43)
* Add missing copyright headers by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#44](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/44)
* Add pre-commit checks by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#45](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/45)
* Improve sslrootcert defaults/documentation by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#46](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/46)
* Use dependency-groups for dev dependencies by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#47](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/47)
* Allow CI/CD workflows to run in parallel without conflicts by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#48](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/48)
* Fix shellcheck warning for missing double quotes by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#49](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/49)
* Migrate to aurora-dsql-orms monorepo by [@amaksimo](https://github.com/amaksimo) in [`924724a`](https://github.com/awslabs/aurora-dsql-orms/commit/924724a)

Full Changelog: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.1.0...python/sqlalchemy/v1.1.1

[Changes][python/sqlalchemy/v1.1.1]


<a id="python/sqlalchemy/v1.1.0"></a>
# [Aurora DSQL dialect for SQLAlchemy v1.1.0 (python/sqlalchemy/v1.1.0)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/sqlalchemy/v1.1.0) - 2026-01-29

This release integrates the [Aurora DSQL Connector for Python](https://github.com/awslabs/aurora-dsql-python-connector), which enables applications to authenticate with Amazon Aurora DSQL using IAM credentials.

A new `create_dsql_engine` method has been introduced, which creates a SQLAlchemy engine that automatically creates a fresh authentication token for each connection. It can use provided IAM credentials, and can be configured using the same parameters as the [Aurora DSQL Connector for Python](https://github.com/awslabs/aurora-dsql-python-connector). See the [updated example code](https://github.com/awslabs/aurora-dsql-sqlalchemy/blob/0df3e45f6d70f103e89e61ac1c2ce93770f9fb13/examples/pet-clinic-app/src/example.py) for more details.

## What's Changed
* Minimize workflow permissions by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#22](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/22)
* updated readme to add discord badge by [@vic-tsang](https://github.com/vic-tsang) in [awslabs/aurora-dsql-sqlalchemy#23](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/23)
* Update Discord badge by [@wcmjunior](https://github.com/wcmjunior) in [awslabs/aurora-dsql-sqlalchemy#24](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/24)
* Use Python connector for IAM authentication by [@amaksimo](https://github.com/amaksimo) in [awslabs/aurora-dsql-sqlalchemy#26](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/26)
* Add uv lock file to pin dependency versions by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#27](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/27)
* Add dependabot config by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#29](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/29)
* Bump astral-sh/setup-uv from 5 to 7 by [@dependabot](https://github.com/dependabot)[bot] in [awslabs/aurora-dsql-sqlalchemy#33](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/33)
* Bump actions/upload-artifact from 4 to 6 by [@dependabot](https://github.com/dependabot)[bot] in [awslabs/aurora-dsql-sqlalchemy#34](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/34)
* Skip empty primary key constraints during processing by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#28](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/28)
* Use GitHub release tag as build version by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#31](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/31)
* Allow passthrough of python connector params by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#30](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/30)
* Bump aws-actions/configure-aws-credentials from 4 to 5 by [@dependabot](https://github.com/dependabot)[bot] in [awslabs/aurora-dsql-sqlalchemy#35](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/35)
* Bump actions/download-artifact from 4 to 7 by [@dependabot](https://github.com/dependabot)[bot] in [awslabs/aurora-dsql-sqlalchemy#36](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/36)
* Ignore gitleaks upgrades by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-sqlalchemy#38](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/38)
* Bump actions/checkout from 4 to 6 by [@dependabot](https://github.com/dependabot)[bot] in [awslabs/aurora-dsql-sqlalchemy#39](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/39)

## New Contributors
* [@amaksimo](https://github.com/amaksimo) made their first contribution in [awslabs/aurora-dsql-sqlalchemy#26](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/26)
* [@dependabot](https://github.com/dependabot)[bot] made their first contribution in [awslabs/aurora-dsql-sqlalchemy#33](https://github.com/awslabs/aurora-dsql-sqlalchemy/pull/33)

**Full Changelog**: https://github.com/awslabs/aurora-dsql-sqlalchemy/compare/v1.0.2...v1.1.0


[Changes][python/sqlalchemy/v1.1.0]


<a id="python/sqlalchemy/v1.0.2"></a>
# [Aurora DSQL dialect for SQLAlchemy v1.0.2 (python/sqlalchemy/v1.0.2)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/sqlalchemy/v1.0.2) - 2026-01-29

- Improved README


[Changes][python/sqlalchemy/v1.0.2]


<a id="python/sqlalchemy/v1.0.1"></a>
# [Aurora DSQL dialect for SQLAlchemy v1.0.1 (python/sqlalchemy/v1.0.1)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/sqlalchemy/v1.0.1) - 2026-01-29

* Updated Pypi description
* Updated python version
* Improved README


[Changes][python/sqlalchemy/v1.0.1]


<a id="python/sqlalchemy/v1.0.0"></a>
# [Aurora DSQL dialect for SQLAlchemy v1.0.0 (python/sqlalchemy/v1.0.0)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/sqlalchemy/v1.0.0) - 2026-01-29

Initial release of Aurora DSQL Dialect for SQLAlchemy

*Provides integration between SQLAlchemy and Aurora DSQL
*See README for full documentation


[Changes][python/sqlalchemy/v1.0.0]


[python/sqlalchemy/v1.1.2]: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.1.1...python/sqlalchemy/v1.1.2
[python/sqlalchemy/v1.1.1]: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.1.0...python/sqlalchemy/v1.1.1
[python/sqlalchemy/v1.1.0]: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.0.2...python/sqlalchemy/v1.1.0
[python/sqlalchemy/v1.0.2]: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.0.1...python/sqlalchemy/v1.0.2
[python/sqlalchemy/v1.0.1]: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.0.0...python/sqlalchemy/v1.0.1
[python/sqlalchemy/v1.0.0]: https://github.com/awslabs/aurora-dsql-orms/tree/python/sqlalchemy/v1.0.0

<!-- Generated by https://github.com/rhysd/changelog-from-release v3.9.1 -->
