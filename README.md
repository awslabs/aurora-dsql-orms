# Aurora DSQL Plugin for DBeaver

A DBeaver plugin that enables connectivity to Amazon Aurora DSQL databases with IAM authentication support.

## Overview

This plugin installs and sets up the [Aurora DSQL Connector for JDBC](https://github.com/awslabs/aurora-dsql-jdbc-connector) for DBeaver to connect to Amazon Aurora DSQL.

Features:
- IAM authentication 
- Custom connection UI for Aurora DSQL endpoints
- Automatic JDBC driver management for the Aurora DSQL connector

## Prerequisites

- **DBeaver**: Version 24.3.5 or later 
- **AWS Credentials**: Configured AWS credentials for IAM authentication
- **Java**: JRE 21 or later (included with DBeaver 24.3.5+)

## Installation Methods

### Install from Update Site 

1. Open DBeaver
2. Go to **Help** → **Install New Software**
3. Click **Add** to add a new repository
4. Enter:
   - **Name**: `Aurora DSQL Plugin`
   - **Location**: `https://awslabs.github.io/aurora-dsql-dbeaver-plugin/repository/`
5. Check **Aurora DSQL Connector for JDBC**
6. Click **Next**, accept the license, and complete the installation
7. Restart DBeaver when prompted

## Developer 

### Prerequisites
- Apache Maven: 3.9.11
- Get a copy of the self-signed Java Key Store (.jks) file (Temporary Signing Method)

1. Run ```mvn clean package  -Dkeystore.password=[JKS_PASSWORD]```
2. Inside the ```com.aws.aurora.dsql.updatesite folder > target > repository``` is the location of the local repo. 
3. Follow the installation instructions above and use the local repo location instead of the URL. 

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
