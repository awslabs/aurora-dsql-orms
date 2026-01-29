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


[python/sqlalchemy/v1.1.0]: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.0.2...python/sqlalchemy/v1.1.0
[python/sqlalchemy/v1.0.2]: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.0.1...python/sqlalchemy/v1.0.2
[python/sqlalchemy/v1.0.1]: https://github.com/awslabs/aurora-dsql-orms/compare/python/sqlalchemy/v1.0.0...python/sqlalchemy/v1.0.1
[python/sqlalchemy/v1.0.0]: https://github.com/awslabs/aurora-dsql-orms/tree/python/sqlalchemy/v1.0.0

<!-- Generated by https://github.com/rhysd/changelog-from-release v3.9.1 -->
