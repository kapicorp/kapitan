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

"references module"

import base64
import errno
import hashlib
import json
import logging
import re
import sys
import os
import yaml

from kapitan.errors import RefFromFuncError, RefBackendError, RefError
from kapitan.errors import RefHashMismatchError
from kapitan.refs.functions import eval_func
from kapitan.utils import PrettyDumper, list_all_paths

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader

logger = logging.getLogger(__name__)

# e.g. ?{ref:my/secret/token} or ?{ref:my/secret/token|func:param1:param2}
REF_TOKEN_TAG_PATTERN = r"(\?{([\w\:\.\-\/]+)([\|\w\:\.\-\/]+)?=*})"


class Ref(object):
    def __init__(self, data, from_base64=False, **kwargs):
        """
        writes data
        set from_base64 to load already base64 encoded data
        """
        self.type_name = 'ref'
        self.encoding = kwargs.get('encoding', 'original')
        # TODO data should be bytes only
        if from_base64:
            self.data = data
        else:
            self.data = base64.b64encode(data).decode()

    def reveal(self):
        # TODO data should be bytes only
        return base64.b64decode(self.data).decode()

    def compile(self):
        # XXX will only work if object read via backend
        return "?{{{}:{}:{}}}".format(self.type_name, self.path, self.hash[:8])

    def __str__(self):
        return "{}".format(self.__dict__)

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        """
        return a new Ref from file at ref_full_path
        the data key in the file must be base64 encoded
        """
        try:
            with open(ref_full_path) as fp:
                obj = yaml.load(fp, Loader=YamlLoader)
                _kwargs = {key: value for key, value in obj.items() if key not in ('data', 'from_base64')}
                kwargs.update(_kwargs)
                return cls(obj['data'], from_base64=True, **kwargs)

        except IOError as ex:
            if ex.errno == errno.ENOENT:
                return None

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new Ref from data and ref_params
        """
        # default encoding to 'original'
        # TODO encoding needs a better place other than kwargs
        encoding = ref_params.kwargs.get('encoding', 'original')
        if encoding == 'original':
            return cls(data.encode(), **ref_params.kwargs)
        elif encoding == 'base64':
            # data already bytes encoded
            return cls(data, **ref_params.kwargs)

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {"data": self.data, "encoding": self.encoding,
                "type": self.type_name}


class RefParams(object):
    def __init__(self, *args, **kwargs):
        "pack params for new Refs from functions"
        self.args = args
        self.kwargs = kwargs


class RefBackend(object):
    def __init__(self, path, ref_type=Ref):
        "Get and create Refs"
        self.path = path
        self.type_name = 'ref'
        self.ref_type = ref_type  # Ref type backend instance manages

    def __getitem__(self, ref_path):
        full_ref_path = os.path.join(self.path, ref_path)
        ref = self.ref_type.from_path(full_ref_path)

        if ref is not None:
            ref.path = ref_path
            ref_path_data = "{}{}".format(ref.path, ref.data)
            ref.hash = hashlib.sha256(ref_path_data.encode()).hexdigest()
            ref.token = "{}:{}:{}".format(ref.type_name, ref.path, ref.hash[:8])
            return ref

        raise KeyError(ref_path)

    def __setitem__(self, ref_path, ref_obj):
        assert(isinstance(ref_obj, self.ref_type))
        full_ref_path = os.path.join(self.path, ref_path)
        os.makedirs(os.path.dirname(full_ref_path), exist_ok=True)

        with open(full_ref_path, 'w') as fp:
            yaml.safe_dump(ref_obj.dump(), stream=fp, default_flow_style=False)

    def __contains__(self, ref_path):
        try:
            self.__getitem__(ref_path)
            return True
        except KeyError:
            return False

    def __iter__(self):
        for full_path in list_all_paths(self.path):
            ref_path = full_path[len(self.path):]
            yield ref_path

    def iteritems(self):
        for k in self.__iter__():
            try:
                v = self.__getitem__(k)
                yield (k, v)
            except KeyError:
                pass


class Revealer(object):
    def __init__(self, ref_controller):
        "reveal files and objects"
        self.ref_controller = ref_controller
        self.regex = re.compile(REF_TOKEN_TAG_PATTERN)

    def reveal_path(self, path):
        "detects if path is file or dir, returns list of RevealObj"
        if os.path.isfile(path):
            content, content_type = self._reveal_file(path)
            return [RevealedObj(content, content_type)]
        elif os.path.isdir(path):
            content_yaml, content_json, content_raw = self._reveal_dir(path)
            revealed_objs = []
            if content_yaml != '':
                revealed_objs.append(RevealedObj(content_yaml, 'yaml'))
            elif content_json != '':
                revealed_objs.append(RevealedObj(content_json, 'json'))
            elif content_raw != '':
                revealed_objs.append(RevealedObj(content_raw, 'raw'))
            return revealed_objs
        else:
            raise FileNotFoundError(path)

    def _reveal_file(self, filename):
        """
        detects filename by extension (.yml/.yaml, .json or otherwise raw)
        reveals secrets in content
        """
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            logger.debug("Revealer: revealing yml file: %s", filename)
            with open(filename) as fp:
                obj = yaml.load(fp, Loader=YamlLoader)
                rev_obj = self.reveal_obj(obj)
                return yaml.dump(rev_obj, Dumper=PrettyDumper, default_flow_style=False, explicit_start=True), 'yaml'
        elif filename.endswith('.json'):
            logger.debug("Revealer: revealing json file: %s", filename)
            with open(filename) as fp:
                obj = json.load(fp)
                rev_obj = self.reveal_obj(obj)
                return json.dumps(rev_obj, indent=4, sort_keys=True), 'json'
        else:
            logger.debug("Revealer: revealing raw file: %s", filename)
            return self.reveal_raw_file(filename), 'raw'

    def _reveal_dir(self, dirname):
        """
        returns tuple with yaml, json, and raw concatenated output for revealed file types
        it does not walk through the dir structure as it skips directories inside dirname
        """
        out_yaml = ''
        out_json = ''
        out_raw = ''
        # find yaml/json/raw files and concatenate output per type
        for f in os.listdir(dirname):
            full_path = os.path.join(dirname, f)
            if not os.path.isfile(full_path):
                pass
            if f.endswith('.yml') or f.endswith('.yaml'):
                out, _ = self._reveal_file(full_path)
                out_yaml += out
            elif f.endswith('.json'):
                out, _ = self._reveal_file(full_path)
                out_json += self._reveal_file(full_path)
            else:
                out, _ = self._reveal_file(full_path)
                out_raw += out

        return out_yaml, out_json, out_raw

    def _reveal_replace_match(self, match_obj):
        """returns decrypted value from tag in match_obj"""
        tag, _, _ = match_obj.groups()
        ref = self.ref_controller[tag]
        logger.debug("Ref: revealing: %s", tag)
        return ref.reveal()

    def _compile_replace_match_with_args(self, **kwargs):
        """returns compile_replace_match function with kwargs"""
        def compile_replace_match(match_obj):
            """returns compile ref value from tag in match_obj"""
            tag, _, _ = match_obj.groups()
            try:
                ref = self.ref_controller[tag]
                return ref.compile()
            # if refs needs to be created from func:
            except RefFromFuncError:
                # create ref from func with kwargs RefParams
                self.ref_controller[tag] = RefParams(**kwargs)
                ref = self.ref_controller[tag]
                return ref.compile()
            # if refs don't exist:
            except KeyError:
                raise RefError("Could not find ref: {}".format(tag))

        return compile_replace_match

    def reveal_raw_file(self, filename):
        """
        read filename and reveal content (per line search and replace) with refs
        set filename=None to read stdin
        returns string with revealed content
        """
        out_raw = ''
        if filename is None:
            for line in sys.stdin:
                revealed = self.regex.sub(self._reveal_replace_match, line)
                out_raw += revealed
        else:
            with open(filename) as fp:
                for line in fp:
                    revealed = self.regex.sub(self._reveal_replace_match, line)
                    out_raw += revealed
        return out_raw

    def compile_raw(self, data, **kwargs):
        """
        read data and compile refs (per line search and replace) with output of ref .compile() method
        kwargs are passed to ref compile function
        returns string with compile content
        """
        compiled = self.regex.sub(self._compile_replace_match_with_args(**kwargs), data)
        return compiled

    def reveal_raw(self, data):
        """
        read data and reveal content (per line search and replace) with refs
        returns string with revealed content
        """
        revealed = self.regex.sub(self._reveal_replace_match, data)
        return revealed

    def reveal_obj(self, obj):
        """recursively updates obj with revealed refs"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self.reveal_obj(v)
        elif isinstance(obj, list):
            obj = [self.reveal_obj(item) for item in obj]
        elif isinstance(obj, str):
            obj = self.regex.sub(self._reveal_replace_match, obj)
        return obj

    def compile_obj(self, obj, **kwargs):
        """
        recursively updates obj with compiled refs
        kwargs are passed to ref compile function
        """
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self.compile_obj(v, **kwargs)
        elif isinstance(obj, list):
            obj = [self.compile_obj(item, **kwargs) for item in obj]
        elif isinstance(obj, str):
            obj = self.regex.sub(self._compile_replace_match_with_args(**kwargs), obj)
        return obj


class RevealedObj(object):
    "Content and content type object type"
    def __init__(self, content, content_type):
        self.content = content
        self.content_type = content_type


class RefController(object):
    def __init__(self, path):
        """
        gets and sets tags for ref type objects.
        auto registers backends
        """
        self.backends = {}
        self.path = path

    def register_backend(self, backend):
        "register backend type"
        assert(isinstance(backend, RefBackend))
        self.backends[backend.type_name] = backend

    def _get_backend(self, type_name):
        "imports and registers backend according to type_name"
        try:
            return self.backends[type_name]
        except KeyError:
            if type_name == 'ref':
                from kapitan.refs.base import RefBackend
                self.register_backend(RefBackend(self.path))
            elif type_name == 'gpg':
                from kapitan.refs.secrets.gpg import GPGBackend
                self.register_backend(GPGBackend(self.path))
            elif type_name == 'gkms':
                from kapitan.refs.secrets.gkms import GoogleKMSBackend
                self.register_backend(GoogleKMSBackend(self.path))
            elif type_name == 'awskms':
                from kapitan.refs.secrets.awskms import AWSKMSBackend
                self.register_backend(AWSKMSBackend(self.path))
            else:
                raise RefBackendError('no backend for ref type: {}'.format(type_name))
        return self.backends[type_name]

    def tag_type(self, tag):
        "returns ref type for tag"
        # ?{ref:my/secret/token} or ?{ref:my/secret/token|func:param1:param2} or ?{ref:my/secret/token:deadbeef}
        _, token, _ = self.tag_params(tag)
        return self.token_type(token)

    def tag_params(self, tag):
        "returns tag parameter tuple with (tag, token, func_str)"
        match = re.match(REF_TOKEN_TAG_PATTERN, tag)
        if match:
            tag, token, func_str = match.groups()
            return tag, token, func_str
        else:
            raise RefError("{}: is not a valid tag".format(tag))

    def token_type(self, token):
        "returns ref type for token"
        attrs = token.split(':')
        type_name = attrs[0]

        # force type_name to register
        self._get_backend(type_name)

        return self.backends[type_name].ref_type

    def token_type_name(self, token):
        "returns ref type name for token"
        attrs = token.split(':')
        type_name = attrs[0]

        return type_name

    def _get_from_token(self, token):
        attrs = token.split(':')

        # "type_name:path/to/ref"
        if len(attrs) == 2:
            type_name = attrs[0]
            path = attrs[1]
            backend = self._get_backend(type_name)
            return backend[path]

        # "type_name:path/to/ref:n0c0ffee"
        elif len(attrs) == 3:
            type_name = attrs[0]
            path = attrs[1]
            hash = attrs[2]
            backend = self._get_backend(type_name)
            ref = backend[path]
            if ref.hash[:8] == hash:
                return ref
            else:
                raise RefHashMismatchError("{}: hash does not match with: {}".format(token, ref.token))
        else:
            return None

    def _set_to_token(self, token, ref_obj):
        attrs = token.split(':')

        if len(attrs) == 2:
            type_name = attrs[0]
            path = attrs[1]
            backend = self._get_backend(type_name)
            assert(isinstance(ref_obj, backend.ref_type))
            backend[path] = ref_obj
        else:
            raise RefError("{}: is not a valid token".format(token))

    def _eval_func_str(self, ctx, func_str):
        """
        evals and updates context ctx for func_str
        returns evaluated ctx
        """
        assert(func_str.startswith('|'))
        funcs = func_str[1:].split('|')

        for func in funcs:
            func_name, *func_params = func.strip().split(':')
            if func_name == 'base64':  # not a real function
                ctx.encode_base64 = True
            else:
                try:
                    eval_func(func_name, ctx, *func_params)
                except KeyError:
                    raise RefError("{}: unknown function".format(func_name))

        return ctx

    def __getitem__(self, key):
        # ?{ref:my/secret/token} or ?{ref:my/secret/token|func:param1:param2} or ?{ref:my/secret/token:deadbeef}
        tag, token, func_str = self.tag_params(key)

        # if there is no function, grab token
        if func_str is None:
            ref = self._get_from_token(token)
            if ref:
                return ref
        else:
            # if there is a function, try grabbing token
            try:
                ref = self._get_from_token(token)
                if ref:
                    return ref
            except KeyError:
                # if func is set and ref doesnt exist,
                # raise RefFromFuncError to indicate new ref needs to be created
                raise RefFromFuncError('{}: does not exist and must be '
                                       'created from function: {}'.format(token, func_str))

        raise KeyError("{}: ref not found".format(tag))

    def __setitem__(self, key, value):
        # ?{ref:my/secret/token} or ?{ref:my/secret/token|func:param1:param2}
        tag, token, func_str = self.tag_params(key)

        if func_str is None and isinstance(value, self.token_type(token)):
            return self._set_to_token(token, value)
        # if function is set, ensure value is RefParams instance
        elif func_str is not None and isinstance(value, RefParams):
            # run _eval_func_str, create ref_obj and run _set_to_token()
            ctx = FunctionContext(None)
            ctx.encode_base64 = False
            ctx.ref_controller = self
            ctx.token = token

            self._eval_func_str(ctx, func_str)
            ref_type = self.token_type(token)

            if ctx.encode_base64:
                b64_data = base64.b64encode(ctx.data.encode())
                # TODO encoding needs a better place other than kwargs
                value.kwargs['encoding'] = 'base64'
                ref_obj = ref_type.from_params(b64_data, value)
            else:
                ref_obj = ref_type.from_params(ctx.data, value)

            return self._set_to_token(token, ref_obj)


class FunctionContext(object):
    def __init__(self, data):
        "Carry context across function evaluation"
        self.data = data
