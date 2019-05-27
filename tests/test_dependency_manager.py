#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import contextlib
import io
import os
import unittest
import tempfile

from kapitan.dependency_manager.git import Git


class GitDependencyTest(unittest.TestCase):

    def test_clone_repo_checkout(self):
        temp_dir = tempfile.mkdtemp()
        Git.cache_dir = temp_dir
        repo_url = 'git@github.com:deepmind/kapitan.git'
        output_path = os.path.join(temp_dir, 'kapitan')
        ref = 'eddde31'
        git_dependency = Git(repo_url, output_path, ref=ref)
        git_dependency.fetch()

        self.assertTrue(os.path.isdir(os.path.join(temp_dir, 'kapitan', 'kapitan')))
        self.assertTrue(os.path.isdir(os.path.join(temp_dir, 'kapitan', 'tests')))

    def test_clone_repo_subdir(self):
        temp_dir = tempfile.mkdtemp()
        Git.cache_dir = temp_dir
        repo_url = 'git@github.com:deepmind/kapitan.git'
        output_path = os.path.join(temp_dir, 'kapitan')
        git_dependency = Git(repo_url, output_path, subdir='tests')
        git_dependency.fetch()

        self.assertTrue(os.path.isdir(output_path))
        self.assertFalse(os.path.isdir(os.path.join(temp_dir, 'tests')))
        self.assertTrue(os.path.isfile(os.path.join(output_path, '__init__.py')))

    def test_repo_cache(self):
        with self.assertLogs(logger='kapitan.dependency_manager.git', level='INFO') as cm, contextlib.redirect_stdout(io.StringIO()):
            temp_dir = tempfile.mkdtemp()
            Git.cache_dir = temp_dir
            repo_url = 'git@github.com:deepmind/kapitan.git'
            output_path = os.path.join(temp_dir, 'kapitan')
            git_dependency = Git(repo_url, output_path, subdir='tests')
            git_dependency.fetch()

            git_dependency = Git(repo_url, output_path, subdir='tests')
            git_dependency.fetch()
            # as of now, we cannot capture stdout with contextlib.redirect_stdout
            # since we only do logger.error(e) in targets.py before exiting
        self.assertTrue(' '.join(cm.output).find('cache loaded') != -1)
