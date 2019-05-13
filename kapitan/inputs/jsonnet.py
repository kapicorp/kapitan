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

import logging
import os
import json

from kapitan.inputs.base import InputType, CompiledFile
from kapitan.resources import search_imports, resource_callbacks
from kapitan.utils import jsonnet_file, prune_empty

logger = logging.getLogger(__name__)


class Jsonnet(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("jsonnet", compile_path, search_paths, ref_controller)

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Write file_path (jsonnet evaluated) items as files to compile_path.
        ext_vars will be passed as parameters to jsonnet_file()
        kwargs:
            output: default 'yaml', accepts 'json'
            prune: default False, accepts True
            reveal: default False, set to reveal refs on compile
            target_name: default None, set to current target being compiled
            indent: default 2
        """
        def _search_imports(cwd, imp):
            return search_imports(cwd, imp, self.search_paths)

        json_output = jsonnet_file(file_path, import_callback=_search_imports,
                                   native_callbacks=resource_callbacks(self.search_paths),
                                   ext_vars=ext_vars)
        output_obj = json.loads(json_output)

        output = kwargs.get('output', 'yaml')
        prune = kwargs.get('prune', False)
        reveal = kwargs.get('reveal', False)
        target_name = kwargs.get('target_name', None)
        indent = kwargs.get('indent', 2)

        if prune:
            output_obj = prune_empty(output_obj)
            logger.debug("Pruned output for: %s", file_path)

        for item_key, item_value in output_obj.items():
            # write each item to disk
            if output == 'json':
                file_path = os.path.join(compile_path, '%s.%s' % (item_key, output))
                with CompiledFile(file_path, self.ref_controller, mode="w", reveal=reveal, target_name=target_name,
                                  indent=indent) as fp:
                    fp.write_json(item_value)
            elif output == 'yaml':
                file_path = os.path.join(compile_path, '%s.%s' % (item_key, "yml"))
                with CompiledFile(file_path, self.ref_controller, mode="w", reveal=reveal, target_name=target_name,
                                  indent=indent) as fp:
                    fp.write_yaml(item_value)
            elif output == 'plain':
                file_path = os.path.join(compile_path, '%s' % item_key)
                with CompiledFile(file_path, self.ref_controller, mode="w", reveal=reveal, target_name=target_name,
                                  indent=indent) as fp:
                    fp.write(item_value)
            else:
                raise ValueError('output is neither "json", "yaml" or "plain"')

    def default_output_type(self):
        return "yaml"
