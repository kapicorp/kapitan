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
from kapitan.utils import list_all_paths

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
        self.component_dir = "inventory/classes"

        self.directory = directory
        self.target_name = target_name.split(',') if target_name else []
        self.compile_input = compile_input.split(',') if compile_input else []
        current_pwd = os.path.dirname(__file__)
        self.templates_directory = os.path.join(current_pwd, 'inputs/templates')

        self.copy_path_list = []



    # copy_tree(templates_directory, directory)
    def get_target_template(self):
        path = os.path.join(self.templates_directory, self.target_dir, self.target_template_name)
        with open(path) as f:
            obj = yaml.safe_load(f.read())
        return obj

    def get_component_template(self):
        path = os.path.join(self.templates_directory, self.component_dir, self.component_template_name)
        with open(path) as f:
            obj = yaml.safe_load(f.read())
        return obj

    def generate_copy(self):
        self.copy_inventory()
        self.copy_target_file()
        self.copy_component_file()
        self.copy_compile_components()
        self.list_new_directory()

    def copy_inventory(self):
        """
            copy all files in inventory except my_target.yml
        """
        template_inventory = os.path.join(self.templates_directory,'inventory')
        new_inventory = os.path.join(self.directory,'inventory')
        shutil.copytree(template_inventory,new_inventory,
                        ignore=shutil.ignore_patterns("my_target.yml"))

    def copy_target_file(self):
        """
            copy target_file to new location with target-name provided by user
            if is empty target-name then copy original file
        """
        target_file = self.get_target_template()
        if len(self.target_name):
            for i in self.target_name:
                target_file['parameters']['target_name'] = i
                path = self.get_new_target_path("%s.yml" % i)
                self.dump_yaml(target_file,path)
        else:
            path = self.get_new_target_path(self.target_template_name)
            self.dump_yaml(target_file, path)

    def copy_component_file(self):
        """
            copy component file `my_component.yml` to new directory
            only copy compile_obj's input_type is in compile-input
            if compile-input is not provided my user copy all compile_obj
            append input_paths of accepted compile_obj to copy_path_list
        """

        component_file = self.get_component_template()
        compile_objs = []
        for compile_obj in component_file['parameters']['kapitan']['compile']:
            if compile_obj['input_type'] in self.compile_input or len(self.compile_input) == 0:
                self.copy_path_list += compile_obj['input_paths']
                compile_objs.append(compile_obj)
        component_file['parameters']['kapitan']['compile'] = compile_objs

        path = self.get_new_component_path()
        self.dump_yaml(component_file, path)

    def copy_compile_components(self):
        """
            copy for files present in copy_path_list to new location
        """
        for path in self.copy_path_list:
            self.copy_components(path)

    def get_new_target_path(self,name):
        path = os.path.join(self.directory, self.target_dir)
        self.handle_directory_creation(path)
        path = os.path.join(path,name)
        return path

    def get_new_component_path(self):
        path = os.path.join(self.directory, self.component_dir)
        self.handle_directory_creation(path)
        path = os.path.join(path,self.component_template_name)
        return path

    def handle_directory_creation(self,path):
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            pass

    def copy_components(self,path):
        """
            copy allowed components to new location
            if directory then copy every entire directory
        """
        template_file_path = os.path.join(self.templates_directory, path)
        new_file_path = os.path.join(self.directory, path)
        if os.path.isdir(template_file_path):
            new_file_path = new_file_path.rstrip('/')
            dirname = os.path.dirname(new_file_path)
            self.handle_directory_creation(dirname)
            shutil.copytree(template_file_path, new_file_path)
        else:
            file_directory = os.path.dirname(new_file_path)
            self.handle_directory_creation(file_directory)
            shutil.copy(template_file_path, new_file_path)



    def dump_yaml(self,obj,path):
        with open(path, 'w') as outfile:
            yaml.dump(obj, outfile, default_flow_style=False)

    def list_new_directory(self):
        """
            list all files in new location
        """
        logger.info("Populated {} with:".format(self.directory))
        for dirName, _, fileList in os.walk(self.directory):
            logger.info('{}'.format(dirName))
            for fname in fileList:
                logger.info('\t {}'.format(fname))
