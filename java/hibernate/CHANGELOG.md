<a id="java/hibernate/v1.0.1"></a>
# [Aurora DSQL Dialect for Hibernate v1.0.1 (java/hibernate/v1.0.1)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/java/hibernate/v1.0.1) - 2026-01-30

This release migrates the Hibernate dialect to the new [Aurora DSQL ORM Adapters monorepo](https://github.com/awslabs/aurora-dsql-orms) and updates tooling/documentation accordingly. The dialect is functionally equivalent to `v1.0.0`.

The Pet Clinic example application now uses the [Aurora DSQL Connector for JDBC](https://github.com/awslabs/aurora-dsql-jdbc-connector) for IAM authentication, replacing manual token generation with the AWS SDK.

Dependencies versions have been updated for both the dialect and example application.

## What's Changed

* Add published dependency to gradle sample by [@elholmit](https://github.com/elholmit) in [awslabs/aurora-dsql-hibernate#32](https://github.com/awslabs/aurora-dsql-hibernate/pull/32)
* Add setup steps to Pet-Clinic readme by [@elholmit](https://github.com/elholmit) in [awslabs/aurora-dsql-hibernate#33](https://github.com/awslabs/aurora-dsql-hibernate/pull/33)
* Add Maven Central release badge by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-hibernate#34](https://github.com/awslabs/aurora-dsql-hibernate/pull/34)
* Add index to Owner, double to Pet, and change SQL logging by [@elholmit](https://github.com/elholmit) in [awslabs/aurora-dsql-hibernate#35](https://github.com/awslabs/aurora-dsql-hibernate/pull/35)
* Bump actions/setup-java from 4 to 5 by [@dependabot](https://github.com/dependabot) in [awslabs/aurora-dsql-hibernate#37](https://github.com/awslabs/aurora-dsql-hibernate/pull/37)
* Bump actions/checkout from 4 to 5 by [@dependabot](https://github.com/dependabot) in [awslabs/aurora-dsql-hibernate#36](https://github.com/awslabs/aurora-dsql-hibernate/pull/36)
* Bump aws-actions/configure-aws-credentials from 4 to 5 by [@dependabot](https://github.com/dependabot) in [awslabs/aurora-dsql-hibernate#38](https://github.com/awslabs/aurora-dsql-hibernate/pull/38)
* Minimize workflow permissions by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-hibernate#39](https://github.com/awslabs/aurora-dsql-hibernate/pull/39)
* Add missing Badges by [@wilsoncarvalho](https://github.com/wilsoncarvalho) in [awslabs/aurora-dsql-hibernate#40](https://github.com/awslabs/aurora-dsql-hibernate/pull/40)
* Update Discord badge by [@wilsoncarvalho](https://github.com/wilsoncarvalho) in [awslabs/aurora-dsql-hibernate#41](https://github.com/awslabs/aurora-dsql-hibernate/pull/41)
* Bump actions/checkout from 5 to 6 by [@dependabot](https://github.com/dependabot) in [awslabs/aurora-dsql-hibernate#42](https://github.com/awslabs/aurora-dsql-hibernate/pull/42)
* Use JDBC connector for IAM authentication by [@amaksimo](https://github.com/amaksimo) in [awslabs/aurora-dsql-hibernate#43](https://github.com/awslabs/aurora-dsql-hibernate/pull/43)
* Allow CI/CD workflows to run in parallel without conflicts by [@danielfrankcom](https://github.com/danielfrankcom) in [awslabs/aurora-dsql-hibernate#44](https://github.com/awslabs/aurora-dsql-hibernate/pull/44)
* Add Hibernate and Django adapters to monorepo by [@amaksimo](https://github.com/amaksimo) in [#7](https://github.com/awslabs/aurora-dsql-orms/pull/7)
* Add CI/CD workflows for Hibernate and Django adapters by [@amaksimo](https://github.com/amaksimo) in [#8](https://github.com/awslabs/aurora-dsql-orms/pull/8)
* Format workflow files by [@danielfrankcom](https://github.com/danielfrankcom) in [#10](https://github.com/awslabs/aurora-dsql-orms/issues/10)
* Format Java files by [@danielfrankcom](https://github.com/danielfrankcom) in [#11](https://github.com/awslabs/aurora-dsql-orms/issues/11)
* Standardize workflow permissions by [@danielfrankcom](https://github.com/danielfrankcom) in [#16](https://github.com/awslabs/aurora-dsql-orms/issues/16)
* Consolidate .gitignore files by [@danielfrankcom](https://github.com/danielfrankcom) in [#17](https://github.com/awslabs/aurora-dsql-orms/issues/17)
* Consolidate docs/licensing by [@danielfrankcom](https://github.com/danielfrankcom) in [#18](https://github.com/awslabs/aurora-dsql-orms/pull/18)
* Update docs to point to new repo by [@danielfrankcom](https://github.com/danielfrankcom) in [#19](https://github.com/awslabs/aurora-dsql-orms/pull/19)
* Update changelog files as part of release by [@danielfrankcom](https://github.com/danielfrankcom) in [#20](https://github.com/awslabs/aurora-dsql-orms/issues/20)
* Wait for CI before releasing by [@danielfrankcom](https://github.com/danielfrankcom) in [#21](https://github.com/awslabs/aurora-dsql-orms/issues/21)
* Bump org.jreleaser from 1.19.0 to 1.21.0 in /java/hibernate/dialect by [@dependabot](https://github.com/dependabot) in [#22](https://github.com/awslabs/aurora-dsql-orms/issues/22)
* Bump io.spring.dependency-management from 1.1.6 to 1.1.7 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#23](https://github.com/awslabs/aurora-dsql-orms/issues/23)
* Bump software.amazon.awssdk:dsql from 2.31.33 to 2.41.17 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#24](https://github.com/awslabs/aurora-dsql-orms/issues/24)
* Bump org.postgresql:postgresql from 42.7.2 to 42.7.9 in /java/hibernate/dialect by [@dependabot](https://github.com/dependabot) in [#26](https://github.com/awslabs/aurora-dsql-orms/issues/26)
* Bump io.spring.javaformat from 0.0.43 to 0.0.47 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#27](https://github.com/awslabs/aurora-dsql-orms/issues/27)
* Bump org.cyclonedx.bom from 1.10.0 to 3.1.0 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#28](https://github.com/awslabs/aurora-dsql-orms/issues/28)
* Bump software.amazon.dsql:aurora-dsql-jdbc-connector from 1.0.0 to 1.3.0 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#29](https://github.com/awslabs/aurora-dsql-orms/issues/29)
* Bump gradle/actions from 4 to 5 by [@dependabot](https://github.com/dependabot) in [#34](https://github.com/awslabs/aurora-dsql-orms/issues/34)
* Bump software.amazon.awssdk:dsql from 2.31.64 to 2.41.17 in /java/hibernate/dialect by [@dependabot](https://github.com/dependabot) in [#36](https://github.com/awslabs/aurora-dsql-orms/issues/36)
* Bump aws-actions/configure-aws-credentials from 4 to 5 by [@dependabot](https://github.com/dependabot) in [#37](https://github.com/awslabs/aurora-dsql-orms/issues/37)
* Bump lewagon/wait-on-check-action from 1.4.1 to 1.5.0 by [@dependabot](https://github.com/dependabot) in [#39](https://github.com/awslabs/aurora-dsql-orms/issues/39)
* Bump org.apache.maven.plugins:maven-checkstyle-plugin from 3.5.0 to 3.6.0 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#41](https://github.com/awslabs/aurora-dsql-orms/issues/41)
* Bump org.webjars.npm:bootstrap from 5.3.3 to 5.3.8 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#42](https://github.com/awslabs/aurora-dsql-orms/issues/42)
* Bump com.gitlab.haynes:libsass-maven-plugin from 0.2.29 to 0.3.4 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#43](https://github.com/awslabs/aurora-dsql-orms/issues/43)
* Bump org.apache.logging.log4j:log4j-core from 2.20.0 to 2.25.3 in /java/hibernate/dialect by [@dependabot](https://github.com/dependabot) in [#47](https://github.com/awslabs/aurora-dsql-orms/issues/47)
* Bump org.graalvm.buildtools.native from 0.10.3 to 0.11.4 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#48](https://github.com/awslabs/aurora-dsql-orms/issues/48)
* Bump org.springframework.boot from 3.3.4 to 4.0.2 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#49](https://github.com/awslabs/aurora-dsql-orms/issues/49)
* Bump gradle-wrapper from 8.13 to 9.3.1 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#53](https://github.com/awslabs/aurora-dsql-orms/issues/53)
* Bump org.apache.maven.plugins:maven-surefire-plugin from 3.5.3 to 3.5.4 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#61](https://github.com/awslabs/aurora-dsql-orms/issues/61)
* Bump software.amazon.awssdk:aws-core from 2.41.17 to 2.41.18 in /java/hibernate/dialect by [@dependabot](https://github.com/dependabot) in [#66](https://github.com/awslabs/aurora-dsql-orms/issues/66)
* Bump software.amazon.awssdk:dsql from 2.41.17 to 2.41.18 in /java/hibernate/examples/pet-clinic-app by [@dependabot](https://github.com/dependabot) in [#67](https://github.com/awslabs/aurora-dsql-orms/issues/67)
* Bump hibernate dialect version to 1.0.1 by [@danielfrankcom](https://github.com/danielfrankcom) in [#77](https://github.com/awslabs/aurora-dsql-orms/issues/77)


## New Contributors

* [@alemaksi](https://github.com/alemaksi) made their first contribution in [awslabs/aurora-dsql-hibernate#43](https://github.com/awslabs/aurora-dsql-hibernate/pull/43)
* [@danielfrankcom](https://github.com/danielfrankcom) made their first contribution in [awslabs/aurora-dsql-hibernate#34](https://github.com/awslabs/aurora-dsql-hibernate/pull/34)
* [@dependabot](https://github.com/dependabot)[bot] made their first contribution in [awslabs/aurora-dsql-hibernate#37](https://github.com/awslabs/aurora-dsql-hibernate/pull/37)
* [@wilsoncarvalho](https://github.com/wilsoncarvalho) made their first contribution in [awslabs/aurora-dsql-hibernate#40](https://github.com/awslabs/aurora-dsql-hibernate/pull/40)

Full Changelog: https://github.com/awslabs/aurora-dsql-orms/compare/java/hibernate/v1.0.0...java/hibernate/v1.0.1

[Changes][java/hibernate/v1.0.1]


<a id="java/hibernate/v1.0.0"></a>
# [Aurora DSQL Dialect for Hibernate v1.0.0 (java/hibernate/v1.0.0)](https://github.com/awslabs/aurora-dsql-orms/releases/tag/java/hibernate/v1.0.0) - 2026-01-29

# Release notes

Initial release of Aurora DSQL Dialect for Hibernate

- Provides integration between Hibernate and Aurora DSQL
- See README for full documentation


[Changes][java/hibernate/v1.0.0]


[java/hibernate/v1.0.1]: https://github.com/awslabs/aurora-dsql-orms/compare/java/hibernate/v1.0.0...java/hibernate/v1.0.1
[java/hibernate/v1.0.0]: https://github.com/awslabs/aurora-dsql-orms/tree/java/hibernate/v1.0.0

<!-- Generated by https://github.com/rhysd/changelog-from-release v3.9.1 -->
