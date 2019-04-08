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

"initialiser module"

import logging
import os
from shutil import copytree, ignore_patterns
from kapitan.utils import parse_yaml, dump_yaml

logger = logging.getLogger(__name__)


class initialise(object):
    """
    Initialise a directory with recommended skeleton structure
    """

    def __init__(self, directory, target, compile_input, classes):
        """
        :directory: path of directory to initialise structure in
        :target: list of targets
        :compile_input: list of kapitan input templates to be loaded
        :classes: list of classes to be generated

        """
        self.directory = directory
        self.target = target
        self.compile_input = compile_input
        self.classes = classes
        self.templates_directory = os.path.join(
                    os.path.dirname(__file__), 'inputs', 'templates'
                )
        self.class_template = os.path.join(
                    self.templates_directory, 'inventory', 'classes',
                    'my_component.yml'
                )
        self.target_template = os.path.join(
                    self.templates_directory, 'inventory', 'targets',
                    'my_target.yml'
                )

    def __call__(self):
        copytree(self.templates_directory, self.directory,
                 ignore=ignore_patterns('my*.yml'))
        self.initialise_class()
        self.initialise_target()
        self.print_log()

    def initialise_class(self):
        """
        initialises classes with given name
        """
        compile_target = parse_yaml(self.class_template)

        # filter out the input_type not required
        for val in compile_target['parameters']['kapitan']['compile']:
            if val['input_type'] not in self.compile_input:
                compile_target['parameters']['kapitan']['compile'].remove(val)

        class_directory = os.path.join(self.directory, 'inventory', 'classes')
        for name in self.classes:
            dump_yaml(os.path.join(
                        class_directory, '{}.yml'.format(name)
                        ), compile_target)

    def initialise_target(self):
        """
        initialises targets

        """
        target_obj = parse_yaml(self.target_template)

        if 'my_component' not in self.classes:
            target_obj['classes'].remove('my_component')
            target_obj['classes'].extend(self.classes)

        target_directory = os.path.join(self.directory, 'inventory', 'targets')
        for name in self.target:
            target_obj['parameters']['target_name'] = name
            dump_yaml(os.path.join(
                        target_directory, '{}.yml'.format(name)
                        ), target_obj)

    def print_log(self):
        logger.info("Populated {} with:".format(self.directory))
        for dirName, subdirList, fileList in os.walk(self.directory):
            logger.info('{}'.format(dirName))
            for fname in fileList:
                logger.info('\t {}'.format(fname))
            # Remove the first entry in the list of sub-directories
            # if there are any sub-directories present
            if len(subdirList) > 0:
                del subdirList[0]
