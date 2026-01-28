# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import re

from setuptools import setup
from setuptools_scm import get_version

GITHUB_URL = "https://github.com/awslabs/aurora-dsql-django"
version = get_version()

# Use default branch for dev versions, tag for releases.
if "dev" in version:
    ref = "version-0"
else:
    ref = f"v{version}"

readme_content = open("README.md").read()


def convert_relative_link(match):
    link_text = match.group(1)
    old_url = match.group(2)
    if old_url.startswith("./") or old_url.startswith("../"):
        raise ValueError(f"Relative links starting with './' or '../' are not allowed: {old_url}")
    new_url = f"{GITHUB_URL}/blob/{ref}/{old_url}"
    print(f"Converting: {old_url} -> {new_url}")
    return f"[{link_text}]({new_url})"


# Links on PyPI require absolute URLs. Replace relative URLs with absolute ones.
long_description = re.sub(
    r"\[([^]]+)]\(((?!https?:)[^)]+)\)",
    convert_relative_link,
    readme_content,
)

setup(long_description=long_description, long_description_content_type="text/markdown")
