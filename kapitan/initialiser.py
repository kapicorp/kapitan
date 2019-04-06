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
import sys
import shutil
import yaml

from distutils.dir_util import copy_tree

logger = logging.getLogger(__name__)

class initialise_skeleton(object):
    def __init__(self,directory,target_name,compile_input):
        """ Initialises a directory with a recommended skeleton structure
        Args:
            directory (string): path which to initialise, directory is assumed to exist
        """
        self.target_template_name = 'my_target.yml'
        self.component_template_name = 'my_component.yml'
        self.target_dir = "inventory/targets"
        self.component_dir = "inventory/targets/classes"

        self.directory = directory
        self.target_name = target_name.split(',') if target_name else []
        self.compile_input = compile_input.split(',') if compile_input else []
        current_pwd = os.path.dirname(__file__)
        self.templates_directory = os.path.join(current_pwd, 'inputs/templates')

        self.copy_path_list = []



    # copy_tree(templates_directory, directory)
    def get_target_template(self,get_data=True):
        path = os.path.join(self.templates_directory, self.target_dir, self.target_template_name)
        if get_data:
            with open(path) as f:
                obj = yaml.safe_load(f.read())
            return obj
        else:
            return path

    def get_component_template(self,get_data=True):
        path = os.path.join(templates_directory, self.component_dir, self.component_template_name)
        if get_data:
            with open(path) as f:
                obj = yaml.safe_load(f.read())
            return obj
        else:
            return path

    def generate_copy(self):
        self.copy_inventory()
        self.copy_target_file()
        self.copy_component_file()
        self.copy_compile_components()
        self.list_new_directory()

    def copy_inventory(self):
        template_inventory = os.path.join(self.templates_directory,'inventory')
        new_inventory = os.path.join(self.directory,'inventory')
        shutil.copytree(template_inventory,new_inventory)

    def copy_target_file(self):
        target_file = self.get_target_template()
        if len(self.target_name):
            for i in self.target_name:
                target_file['parameters']['target_name'] = i
                path = self.get_new_target_path("%s.yml" % i)
                self.dump_yaml(target_file,path)
            os.remove(os.path.join(self.directory, self.target_dir, self.target_template_name))

    def copy_component_file(self):

        component_file = self.get_component_template()
        if len(self.compile_input):
            compile_objs = []
            for compile_obj in component_file['parameters']['kapitan']['compile']:
                if compile_obj['input_type'] in self.compile_input:
                    self.copy_path_list += compile_obj['input_paths']
                    compile_objs += compile_obj
                component_file['parameters']['kapitan']['compile'] = compile_objs

        path = self.get_new_component_path(self.get_component_template(False))
        self.dump_yaml(component_file,path)

    def copy_compile_components(self):
        for i in copy_path_list:
            copy_component_file(i)



    def get_new_target_path(self,name):
        path = os.path.join(self.directory, self.target_dir)
        self.handle_directory_creation(path)
        path = os.path.join(path,name)
        return path

    def get_new_component_path(self,name):
        path = os.path.join(self.directory, self.component_dir)
        self.handle_directory_creation(path)
        path = os.path.join(path,name)
        return path

    def handle_directory_creation(self,path):
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            pass

    def copy_component_file(self,path):
        template_file_path = os.path.join(self.templates_directory, path)
        new_file_path = os.path.join(self.directory, path)

        self.handle_directory_creation(new_file_path)

        shutil.copy(template_file_path, new_file_path)


    def dump_yaml(self,obj,path):
        with open(path, 'w') as outfile:
            yaml.dump(obj, outfile, default_flow_style=False)

    def list_new_directory(self):
        logger.info("Populated {} with:".format(self.directory))
        for dirName, _, fileList in os.walk(self.directory):
            logger.info('{}'.format(dirName))
            for fname in fileList:
                logger.info('\t {}'.format(fname))
