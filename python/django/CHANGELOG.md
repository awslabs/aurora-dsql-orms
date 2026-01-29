<a id="python/django/v0.3.0"></a>
# [Aurora DSQL adapter for Django v0.3.0 (python/django/v0.3.0)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/django/v0.3.0) - 2026-01-29

This release removes support for Python 3.8, which is end of life according to [python.org](https://devguide.python.org/versions/).

## What's Changed
* Update changelog for v0.2.1 by [@github-actions](https://github.com/github-actions)[bot] in [awslabs/aurora-dsql-django#73](https://github.com/awslabs/aurora-dsql-django/pull/73)
* Clone whole repo for tag metadata by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#70](https://github.com/awslabs/aurora-dsql-django/pull/70)
* Remove Python 3.8 support by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#74](https://github.com/awslabs/aurora-dsql-django/pull/74)
* Fix license deprecation warnings by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#75](https://github.com/awslabs/aurora-dsql-django/pull/75)


**Full Changelog**: https://github.com/awslabs/aurora-dsql-django/compare/v0.2.1...v0.3.0


[Changes][python/django/v0.3.0]


<a id="python/django/v0.2.1"></a>
# [Aurora DSQL adapter for Django v0.2.1 (python/django/v0.2.1)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/django/v0.2.1) - 2026-01-29

This release fixes the relative links shown on the PyPI project page. There should be no library behavior change.

## What's Changed
* Update changelog for v0.2.0 by [@github-actions](https://github.com/github-actions)[bot] in [awslabs/aurora-dsql-django#68](https://github.com/awslabs/aurora-dsql-django/pull/68)
* Replace relative links in markdown files during build by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#69](https://github.com/awslabs/aurora-dsql-django/pull/69)
* Add content type to PyPI description by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#72](https://github.com/awslabs/aurora-dsql-django/pull/72)


**Full Changelog**: https://github.com/awslabs/aurora-dsql-django/compare/v0.2.0...v0.2.1


[Changes][python/django/v0.2.1]


<a id="python/django/v0.2.0"></a>
# [Aurora DSQL adapter for Django v0.2.0 (python/django/v0.2.0)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/django/v0.2.0) - 2026-01-29

This release includes the following changes:
- Added documentation for known issues and workarounds
- Support for `CREATE INDEX ASYNC`
- Improved UUID primary key behavior when using `AutoField`
- Improved migration support
- Clear error messages for unsupported features during migrations
- Disabled server-side cursors by default (not supported by DSQL)

This release defines and verifies support for the following Django versions:
- Django 4.2.x (LTS)
- Django 5.0.x
- Django 5.1.x
- Django 5.2.x (LTS)

The release also adds verified support for Python 3.13.

## What's Changed
* Remove template to use default template to use default by [@imforster](https://github.com/imforster) in [awslabs/aurora-dsql-django#38](https://github.com/awslabs/aurora-dsql-django/pull/38)
* Bump version for closed-issue-message by [@imforster](https://github.com/imforster) in [awslabs/aurora-dsql-django#39](https://github.com/awslabs/aurora-dsql-django/pull/39)
* Add PyPI release badge by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#40](https://github.com/awslabs/aurora-dsql-django/pull/40)
* Bump actions/checkout from 4 to 5 by [@dependabot](https://github.com/dependabot)[bot] in [awslabs/aurora-dsql-django#42](https://github.com/awslabs/aurora-dsql-django/pull/42)
* Bump actions/setup-python from 5 to 6 by [@dependabot](https://github.com/dependabot)[bot] in [awslabs/aurora-dsql-django#44](https://github.com/awslabs/aurora-dsql-django/pull/44)
* Bump actions/github-script from 7 to 8 by [@dependabot](https://github.com/dependabot)[bot] in [awslabs/aurora-dsql-django#43](https://github.com/awslabs/aurora-dsql-django/pull/43)
* Bump aws-actions/configure-aws-credentials from 4 to 5 by [@dependabot](https://github.com/dependabot)[bot] in [awslabs/aurora-dsql-django#45](https://github.com/awslabs/aurora-dsql-django/pull/45)
* Improve migration support using `CREATE INDEX ASYNC` by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#47](https://github.com/awslabs/aurora-dsql-django/pull/47)
* Remove unnecessary foreign key operation overrides by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#48](https://github.com/awslabs/aurora-dsql-django/pull/48)
* Use `uv` tooling for build by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#52](https://github.com/awslabs/aurora-dsql-django/pull/52)
* Disable check constraints via feature flag by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#49](https://github.com/awslabs/aurora-dsql-django/pull/49)
* Clean up expression index handling by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#50](https://github.com/awslabs/aurora-dsql-django/pull/50)
* Add documented support for Python 3.13 by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#55](https://github.com/awslabs/aurora-dsql-django/pull/55)
* Add repo link to published metadata by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#57](https://github.com/awslabs/aurora-dsql-django/pull/57)
* Switch to setuptools-scm for dynamic versioning by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#58](https://github.com/awslabs/aurora-dsql-django/pull/58)
* Automatically update CHANGELOG.md on release by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#59](https://github.com/awslabs/aurora-dsql-django/pull/59)
* Remove no-op overrides for ALTER TABLE operations by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#51](https://github.com/awslabs/aurora-dsql-django/pull/51)
* Allow release workflow to be temporarily invoked manually by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#60](https://github.com/awslabs/aurora-dsql-django/pull/60)
* Update changelog for v0.1.0 by [@github-actions](https://github.com/github-actions)[bot] in [awslabs/aurora-dsql-django#62](https://github.com/awslabs/aurora-dsql-django/pull/62)
* Use built-in changelog PR creation by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#61](https://github.com/awslabs/aurora-dsql-django/pull/61)
* Fix foreign key references to UUID primary key type by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#53](https://github.com/awslabs/aurora-dsql-django/pull/53)
* Disable server-side cursors by default by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#54](https://github.com/awslabs/aurora-dsql-django/pull/54)
* Improve documentation for known issues by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#56](https://github.com/awslabs/aurora-dsql-django/pull/56)
* Add publishing to release workflow by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#63](https://github.com/awslabs/aurora-dsql-django/pull/63)
* Format files with ruff by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#64](https://github.com/awslabs/aurora-dsql-django/pull/64)
* Ignore ruff formatting commit during git blame by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#65](https://github.com/awslabs/aurora-dsql-django/pull/65)
* Add Django version matrix testing to CI/CD workflow by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#66](https://github.com/awslabs/aurora-dsql-django/pull/66)
* Remove extra README heading by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-django#67](https://github.com/awslabs/aurora-dsql-django/pull/67)

## New Contributors
* [@imforster](https://github.com/imforster) made their first contribution in [awslabs/aurora-dsql-django#38](https://github.com/awslabs/aurora-dsql-django/pull/38)
* [@danielfrankcom](https://github.com/danielfrankcom) made their first contribution in [awslabs/aurora-dsql-django#40](https://github.com/awslabs/aurora-dsql-django/pull/40)
* [@dependabot](https://github.com/dependabot)[bot] made their first contribution in [awslabs/aurora-dsql-django#42](https://github.com/awslabs/aurora-dsql-django/pull/42)
* [@github-actions](https://github.com/github-actions)[bot] made their first contribution in [awslabs/aurora-dsql-django#62](https://github.com/awslabs/aurora-dsql-django/pull/62)

**Full Changelog**: https://github.com/awslabs/aurora-dsql-django/compare/v0.1.0...v0.2.0


[Changes][python/django/v0.2.0]


<a id="python/django/v0.1.0"></a>
# [Aurora DSQL adapter for Django v0.1.0 (python/django/v0.1.0)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/python/django/v0.1.0) - 2026-01-29

## What's Changed

Initial version of the [Aurora DSQL](https://aws.amazon.com/rds/aurora/dsql/) Django adapter.

**Full Changelog**: [link](https://github.com/awslabs/aurora-dsql-django/commits/v0.1.0)


[Changes][python/django/v0.1.0]


[python/django/v0.3.0]: https://github.com/awslabs/aurora-dsql-orms/compare/python/django/v0.2.1...python/django/v0.3.0
[python/django/v0.2.1]: https://github.com/awslabs/aurora-dsql-orms/compare/python/django/v0.2.0...python/django/v0.2.1
[python/django/v0.2.0]: https://github.com/awslabs/aurora-dsql-orms/compare/python/django/v0.1.0...python/django/v0.2.0
[python/django/v0.1.0]: https://github.com/awslabs/aurora-dsql-orms/tree/python/django/v0.1.0

<!-- Generated by https://github.com/rhysd/changelog-from-release v3.9.1 -->
