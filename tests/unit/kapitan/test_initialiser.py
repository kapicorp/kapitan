# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from unittest.mock import patch

import pytest

from kapitan.errors import KapitanError
from kapitan.initialiser import initialise_skeleton


@pytest.mark.usefixtures("local_http_server", "seeded_git_repo")
class TestInitialiser:
    def test_initialise_skeleton_success(self, tmp_path):
        template_path = Path(self.seeded_git_repo)

        target_dir = tmp_path / "skeleton"
        target_dir.mkdir()

        initialise_skeleton(
            self._create_args(str(target_dir), template_git_url=str(template_path))
        )

        rendered_file = target_dir / "README.md"
        assert rendered_file.is_file()

    @patch("kapitan.initialiser.run_copy")
    def test_initialise_skeleton_non_empty_dir(self, mocked_run_copy, tmp_path):
        dummy_file = tmp_path / "dummy.txt"
        dummy_file.write_text("This is a dummy file", encoding="utf-8")

        with pytest.raises(KapitanError):
            initialise_skeleton(
                self._create_args(
                    str(tmp_path),
                    template_git_url=self.httpserver.url_for("/kapitan-template.git"),
                )
            )

        mocked_run_copy.assert_not_called()

    def _create_args(self, target_dir, template_git_url):
        """Helper function to create Namespace object for testing."""
        return type(
            "args",
            (object,),
            {
                "template_git_url": template_git_url,
                "checkout_ref": "master",
                "directory": target_dir,
            },
        )


def test_initialise_skeleton_logs_current_directory_path(monkeypatch, tmp_path, caplog):
    target_dir = tmp_path / "empty"
    target_dir.mkdir()
    monkeypatch.chdir(target_dir)

    run_copy_calls = {}
    monkeypatch.setattr(
        "kapitan.initialiser.run_copy",
        lambda *args, **kwargs: run_copy_calls.update({"args": args, "kwargs": kwargs}),
    )

    args = type(
        "args",
        (object,),
        {
            "template_git_url": "https://example.com/template.git",
            "checkout_ref": "main",
            "directory": ".",
        },
    )

    with caplog.at_level("INFO", logger="kapitan.initialiser"):
        initialise_skeleton(args)

    assert run_copy_calls["kwargs"]["dst_path"] == str(target_dir.resolve())
    assert any(
        "Successfully initialised: run `kapitan --version`" in m
        for m in caplog.messages
    )
