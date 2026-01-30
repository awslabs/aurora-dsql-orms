# Aurora DSQL Dialect for Hibernate - Developer instructions

## Building from source

Building the Aurora DSQL dialect requires Java 17 or greater. The dialect uses [Gradle](https://gradle.org/) to build and
test the dialect.

From a terminal in the [dialect](../dialect) directory, you can run the full build with:

`./gradlew build`

To assemble the Jar without running any tests use:

`./gradlew assemble`

A Jar containing the dialect will be produced at `build/libs/aurora-dsql-hibernate-dialect-1.0.1.jar`. This Jar can
then be used in the Pet-Clinic sample or in your Hibernate application.

## Running integration tests

There is a suite of integration tests that can be run to test the dialect. To execute them you will need access
to an Aurora DSQL cluster. You must have an AWS account, and have your default credentials and AWS Region
configured as described in the [Globally configuring AWS SDKs and tools](https://docs.aws.amazon.com/credref/latest/refdocs/creds-config-files.html)
guide.

1. Set environment variables:
    1. `export CLUSTER_ENDPOINT=<your dsql cluster>`
    2. `export REGION=<your dsql cluster's region>`
    3. `export RUN_INTEGRATION=TRUE`
2. Run the tests (`-i` optionally provides more logging):
   1. `./gradlew test -i` to run all tests including unit tests
   2. `./gradlew test --tests "software.amazon.dsql.integration.* -i`  for all integration tests
   3. `./gradlew test --tests <Class Name> -i`  for a specific test class
3. An HTML test report will be automatically generated at `build/reports/tests/index.html`.

