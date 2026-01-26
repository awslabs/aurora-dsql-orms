# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import re

from hatchling.metadata.plugin.interface import MetadataHookInterface

GITHUB_URL = "https://github.com/awslabs/aurora-dsql-tortoise-orm"


class ReadmeMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "readme"

    def update(self, metadata):
        readme_path = self.root + "/README.md"
        content = open(readme_path).read()

        version = metadata.get("version", "")
        ref = "main" if "dev" in version else version

        def convert_relative_link(match):
            link_text, old_url = match.group(1), match.group(2)
            new_url = f"{GITHUB_URL}/blob/{ref}/{old_url}"
            return f"[{link_text}]({new_url})"

        content = re.sub(r"\[([^]]+)]\(((?!https?://)[^)]+)\)", convert_relative_link, content)
        metadata["readme"] = {"content-type": "text/markdown", "text": content}
