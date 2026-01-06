#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"initialiser module tests"

from pathlib import Path
from unittest.mock import patch

import pytest

from kapitan.errors import KapitanError
from kapitan.initialiser import initialise_skeleton


@pytest.mark.usefixtures("local_http_server", "seeded_git_repo")
class TestInitialiser:
    def test_initialise_skeleton_success(self, temp_dir):
        """
        Verify that initialise_skeleton succeeds when target directory is empty
        """
        template_path = Path(self.seeded_git_repo)

        target_dir = Path(temp_dir) / "skeleton"
        target_dir.mkdir()

        initialise_skeleton(
            self._create_args(str(target_dir), template_git_url=str(template_path))
        )

        rendered_file = target_dir / "README.md"
        assert rendered_file.is_file()

    @patch("kapitan.initialiser.run_copy")
    def test_initialise_skeleton_non_empty_dir(self, mocked_run_copy, temp_dir):
        """
        Verify that initialise_skeleton logs an error when target directory is not empty
        """
        dummy_file = Path(temp_dir) / "dummy.txt"
        dummy_file.write_text("This is a dummy file", encoding="utf-8")

        with pytest.raises(KapitanError):
            initialise_skeleton(
                self._create_args(
                    temp_dir,
                    template_git_url=self.httpserver.url_for("/kapitan-template.git"),
                )
            )

        mocked_run_copy.assert_not_called()

    def _create_args(self, target_dir, template_git_url):
        """Helper function to create Namespace object for testing"""
        return type(
            "args",
            (object,),
            {
                "template_git_url": template_git_url,
                "checkout_ref": "master",
                "directory": target_dir,
            },
        )
