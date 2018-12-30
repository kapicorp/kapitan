#!/usr/bin/env python3
#
# Copyright 2018 The Kapitan Authors
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

from addict import Dict
import logging
import importlib.util
import json
import os
from pprint import pprint
import sys
import yaml

from kapitan.errors import CompileError
from kapitan.inputs.base import InputType, CompiledFile
from kapitan.resources import inventory
from kapitan.utils import render_jinja2, prune_empty

logger = logging.getLogger(__name__)


class Kadet(InputType):
    def __init__(self, compile_path, search_paths, ref_controller):
        super().__init__("kadet", compile_path, search_paths, ref_controller)

    def compile_file(self, file_path, compile_path, ext_vars, **kwargs):
        """
        Write file_path (kadet evaluated) items as files to compile_path.
        ext_vars will be passed as parameters to kadet TODO ??
        kwargs:
            output: default 'yaml', accepts 'json'
            prune: default False
            reveal: default False, set to reveal refs on compile
            target_name: default None, set to current target being compiled
            indent: default 2
        """
        if not os.path.isdir(file_path):
            raise CompiledFile("file_path: {} must be a directory".format(file_path))

        module_name = os.path.basename(os.path.normpath(file_path))
        init_path = os.path.join(file_path, '__init__.py')
        spec = importlib.util.spec_from_file_location('kadet_module_'+module_name, init_path)
        kadet_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = kadet_module # TODO insert only once
        spec.loader.exec_module(kadet_module) # TODO load only once
        logger.debug('Kadet.compile_file: spec.name: %s', spec.name)

        output = kwargs.get('output', 'yaml')
        prune = kwargs.get('prune', False)
        reveal = kwargs.get('reveal', False)
        target_name = kwargs.get('target_name', None)
        indent = kwargs.get('indent', 2)

        output_obj = kadet_module.main().to_dict()
        if prune:
            output_obj = prune_empty(output_obj)

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
            else:
                raise ValueError('output is neither "json" or "yaml"')
            logger.debug("Pruned output for: %s", file_path)

    def default_output_type(self):
        return "yaml"

class BaseObj(object):
    def __init__(self, init_as={}, **kwargs):
        """
        returns a BaseObj
        set init_as to initialise self.root
        use kwargs to set values in self (starting with _)
        use kwargs to set values in self.root
        values in self.root are returned as dict via self.to_dict()
        """
        self.root = Dict(init_as)
        self._parse_kwargs(kwargs)
        self.new()
        self.body()

    @classmethod
    def from_json(cls, file_path, **kwargs):
        """
        returns a BaseObj initialised with json content
        from file_path
        """
        with open(file_path) as fp:
            json_obj = json.load(fp)
            return cls(init_as=json_obj, **kwargs)

    @classmethod
    def from_yaml(cls, file_path, **kwargs):
        """
        returns a BaseObj initialised with yaml content
        from file_path
        """
        with open(file_path) as fp:
            yaml_obj = yaml.safe_load(fp)
            return cls(init_as=yaml_obj, **kwargs)

    def _parse_kwargs(self, kwargs):
        """
        sets priv and root values from kwargs
        kwargs keys starting with _ are private
        any other keys are set in self.root
        """
        for k, v in kwargs.items():
            if k.startswith('_'):
                setattr(self, k, v)
            else:
                setattr(self.root, k, v)

    def need(self, key, msg="key and value needed"):
        """
        requires that key is set in root
        errors with msg if key not set
        """
        err_msg ='{}: "{}": {}'.format(self.__class__.__name__, key, msg)
        if key.startswith('_') and not hasattr(self, key):
            raise Exception(err_msg)
        if key not in self.root:
            raise Exception(err_msg)

    def new(self):
        """
        initialise need()ed keys for
        a new BaseObj
        """
        pass

    def body(self):
        """
        set values/logic for self.root
        """
        pass

    def _to_dict(self, obj):
        """
        recursively update obj should it contain other
        BaseObj values
        """
        if isinstance(obj, BaseObj):
            for k, v in obj.root.items():
                obj.root[k] = self._to_dict(v)
            # BaseObj needs to return to_dict()
            return obj.root.to_dict()
        elif isinstance(obj, list):
            obj = [self._to_dict(item) for item in obj]
            # list has no .to_dict, return itself
            return obj
        elif isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self._to_dict(v)
            # dict has no .to_dict, return itself
            return obj

        # anything else, return itself
        return obj

    def to_dict(self):
        """
        returns object dict
        """
        return self._to_dict(self)


# XXX TEST TEST
# TODO move this to proper tests
if __name__ == '__main__':
    class Deployment(BaseObj):
        def new(self):
            self.need('z')
            self.root['ola'] = 1
            self.root.ole = 2
            self.root.oli = {'x': BaseObj(a=1, b=2)}
            class MyThing(BaseObj):
                def body(self):
                    self.root.yoda = 3
                    class OtherThing(BaseObj):
                        def new(self):
                            self.need('stuff', 'got no stuff')
                        def body(self):
                            self.root.yada = 4
                    self.root.otherthing = OtherThing(a=3, stuff=666)
            self.root.mything = MyThing()
            self.root.things = [MyThing(y=3), MyThing(u=9, f=[MyThing(p=9)])]


    d = Deployment(a=2, z=3, _c=4, w={'a': 34})
    pprint(d.to_dict())
    f = Deployment(a=2, z=3, _c=4, w={'b': 34})
    f.root.z = 69
    pprint(f.to_dict())
    b = BaseObj.from_json("test.json", andthis="also")
    pprint(b.to_dict())
    b = BaseObj.from_yaml("test.yaml", andthis="too")
    pprint(b.to_dict())
