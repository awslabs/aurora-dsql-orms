# Aurora DSQL adapter for Django

[![GitHub](https://img.shields.io/badge/github-awslabs/aurora--dsql--orms-blue?logo=github)](https://github.com/awslabs/aurora-dsql-orms)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](https://github.com/awslabs/aurora-dsql-orms/blob/main/LICENSE)
[![PyPI - Version](https://img.shields.io/pypi/v/aurora-dsql-django)](https://pypi.org/project/aurora-dsql-django)
[![Discord chat](https://img.shields.io/discord/1435027294837276802.svg?logo=discord)](https://discord.com/invite/nEF6ksFWru)

This is the adapter for enabling development of Django applications using Aurora DSQL.

## Requirements

### Django

Aurora DSQL adapter for Django supports Django 4.2+ with the following versions:
- Django 4.2.x (LTS)
- Django 5.0.x
- Django 5.1.x
- Django 5.2.x (LTS)

### Required Python versions

aurora_dsql_django requires Python 3.10 or later.

Please see the link below for more detail to install Python:

* [Python Installation](https://www.python.org/downloads/)

### AWS credentials

Aurora DSQL Django adapter generates the IAM db auth token for every connection.
DB auth token is generated using AWS credentials. You must have configured valid
AWS credentials to be able to use the adapter. If not the connection to the 
cluster will not succeed.

## Getting Started

First, install the adapter using pip:

```pip install aurora_dsql_django```

### Define Aurora DSQL as the Engine for the Django App

Change the ``DATABASES`` variable in ``settings.py`` of your Django app. An example
is show below

```python
   DATABASES = {
        'default': {
            'HOST': '<your_cluster_id>.dsql.<region>.on.aws',
            'USER': 'admin', # or another user you have defined
            'NAME': 'postgres',
            'ENGINE': 'aurora_dsql_django',
            'OPTIONS': {
                'sslmode': 'require',
                # (optional) AWS profile name for credentials
                # 'profile': 'my-aws-profile',
                # (optional) Token duration in seconds (default: 900)
                # 'token_duration_secs': 900,
            }
        }
    }
```

If you need certificate verification, use `'sslmode': 'verify-full'` with `'sslrootcert'`:

```python
'OPTIONS': {
    'sslmode': 'verify-full',
    'sslrootcert': '/path/to/cert.pem',  # or omit to use system certs
}
```

For more info follow the [Aurora DSQL with Django example](examples/pet-clinic-app/README.md)

## Features and Limitations

- **[Adapter Behavior](reference/ADAPTER_BEHAVIOR.md)** - How the Aurora DSQL adapter for Django modifies Django behavior for Aurora DSQL compatibility
- **[Known Issues](reference/KNOWN_ISSUES.md)** - Known limitations and workarounds

## Development

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and then:

```
$ git clone https://github.com/awslabs/aurora-dsql-orms
$ cd aurora-dsql-orms/python/django
$ uv sync
```

`uv` will automatically install the correct Python version and manage the virtual environment.

### Running Tests

You can run the unit tests with this command:

```
$ pytest --cov=aurora_dsql_django aurora_dsql_django/tests/unit/ --cov-report=xml
```

You can run the integration tests with this command:
```
$ export CLUSTER_ENDPOINT=<your cluster endpoint>
$ export DJANGO_SETTINGS_MODULE=aurora_dsql_django.tests.test_settings
$ pytest -v aurora_dsql_django/tests/integration/
```

### Documentation 

Sphinx is used for documentation. You can generate HTML locally with the following:

```
$ uv sync
$ uv run sphinx-build docs/source build
```

## Getting Help

Please use these community resources for getting help.
* Open a support ticket with [AWS Support](http://docs.aws.amazon.com/awssupport/latest/user/getting-started.html).
* If you think you may have found a bug, please open an [issue](https://github.com/awslabs/aurora-dsql-orms/issues/new).

## Opening Issues

If you encounter a bug with the Aurora DSQL Django adapter, we would like to hear about it. Please search the [existing issues](https://github.com/awslabs/aurora-dsql-orms/issues) and see if others are also experiencing the issue before opening a new issue. When opening a new issue please follow the template.

The GitHub issues are intended for bug reports and feature requests. For help and questions with using Aurora DSQL Django adapter, please make use of the resources listed in the [Getting Help](#getting-help) section. Keeping the list of open issues lean will help us respond in a timely manner.

## License

This library is licensed under the Apache 2.0 License.
