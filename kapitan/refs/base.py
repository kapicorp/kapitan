# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"references module"

import base64
import errno
import hashlib
import json
import logging
import os
import re
import sys
from contextlib import contextmanager
from functools import lru_cache

import yaml

from kapitan.errors import RefBackendError, RefError, RefFromFuncError, RefHashMismatchError
from kapitan.refs.functions import eval_func, get_func_lookup
from kapitan.utils import PrettyDumper, list_all_paths

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader

logger = logging.getLogger(__name__)

# e.g. ?{ref:my/secret/token} or ?{ref:my/secret/token||func:param1:param2}
# e.g  ?{ref:basepayloadhere==:embedded} (for embedded refs)
REF_TOKEN_TAG_PATTERN = r"(\?{(\w+:[\w\-\.\@\=\/\:]+)(\|(?:(?:\|\w+)(?::\S*)*)+)?\=*})"
REF_TOKEN_SUBVAR_PATTERN = r"(@[\w\.\-\_]+)"


class PlainRef(object):
    def __init__(self, data, **kwargs):
        """
        writes plain data
        """
        self.type_name = "plain"
        self.encoding = kwargs.get("encoding", "original")
        self.embedded_subvar_path = kwargs.get("embedded_subvar_path", None)
        self.data = data

    def reveal(self):
        return self.data

    def _get_value_in_yaml_path(self, d, yaml_path):
        """using the sub-variable path as nested keys, returns the value in the dictionary"""
        keys = yaml_path.split(".")
        value = d
        for key in keys:
            value = value[key]

        return value

    def compile(self):
        # plain is not using the reveal function, and so we want to look for subvars here
        if self.embedded_subvar_path:
            data = base64.b64decode(self.data).decode("utf-8") if self.encoding == "base64" else self.data
            yaml_data = yaml.load(data, Loader=YamlLoader)
            if not isinstance(yaml_data, dict):
                raise RefError(
                    "PlainRef: revealed secret is not in embedded yaml, "
                    "cannot access sub-variable at {}".format(self.embedded_subvar_path)
                )
            try:
                logger.debug('PlainRef: embedded sub-variable path "%s"', self.embedded_subvar_path)
                value = self._get_value_in_yaml_path(yaml_data, self.embedded_subvar_path)
                return base64.b64encode(value.encode("utf-8")) if self.encoding == "base64" else value
            except KeyError:
                raise RefError(
                    "PlainRef: cannot access sub-variable key {}".format(self.embedded_subvar_path)
                )
        else:
            return self.data

    def __str__(self):
        return "{}".format(self.__dict__)

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        """
        return a new PlainRef from file at ref_full_path
        """
        try:
            with open(ref_full_path) as fp:
                obj = yaml.load(fp, Loader=YamlLoader)
                _kwargs = {key: value for key, value in obj.items() if key not in ("data",)}
                kwargs.update(_kwargs)
                return cls(obj["data"], **kwargs)

        except IOError as ex:
            if ex.errno == errno.ENOENT:
                return None

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new PlainRef from data and ref_params
        """
        # default encoding to 'original'
        # TODO encoding needs a better place other than kwargs
        encoding = ref_params.kwargs.get("encoding", "original")
        if encoding == "original":
            return cls(data.encode(), **ref_params.kwargs)
        elif encoding == "base64":
            # data already bytes encoded
            return cls(data, **ref_params.kwargs)

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {
            "data": self.data.decode(),
            "encoding": self.encoding,
            "type": self.type_name,
        }


class RefParams(object):
    def __init__(self, *args, **kwargs):
        "pack params for new Refs from functions"
        self.args = args
        self.kwargs = kwargs


class PlainRefBackend(object):
    def __init__(self, path, ref_type=PlainRef, **ref_kwargs):
        "Get and create PlainRefs"
        self.path = path
        self.type_name = "plain"
        self.ref_type = ref_type
        self.ref_kwargs = ref_kwargs

    def __getitem__(self, ref_path):
        # remove the substring notation, if any
        ref_file_path = re.sub(REF_TOKEN_SUBVAR_PATTERN, "", ref_path)
        full_ref_path = os.path.join(self.path, ref_file_path)
        ref = self.ref_type.from_path(full_ref_path, **self.ref_kwargs)

        if ref is not None:
            ref.path = ref_path
            ref_path_data = "{}{}".format(ref_file_path, ref.data)
            ref.hash = hashlib.sha256(ref_path_data.encode()).hexdigest()
            ref.token = "{}:{}:{}".format(ref.type_name, ref.path, ref.hash[:8])

            # if subvar is set, save path in 'embedded_subvar_path' key
            subvar = ref_path.split("@")
            if len(subvar) > 1:
                ref.embedded_subvar_path = subvar[1]
            return ref

        raise KeyError(ref_path)

    def __setitem__(self, ref_path, ref_obj):
        assert isinstance(ref_obj, self.ref_type)
        full_ref_path = os.path.join(self.path, ref_path)
        os.makedirs(os.path.dirname(full_ref_path), exist_ok=True)

        with open(full_ref_path, "w") as fp:
            yaml.safe_dump(ref_obj.dump(), stream=fp, default_flow_style=False)

    def __contains__(self, ref_path):
        try:
            self.__getitem__(ref_path)
            return True
        except KeyError:
            return False

    def __iter__(self):
        for full_path in list_all_paths(self.path):
            ref_path = full_path[len(self.path) :]
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
            if content_yaml != "":
                revealed_objs.append(RevealedObj(content_yaml, "yaml"))
            elif content_json != "":
                revealed_objs.append(RevealedObj(content_json, "json"))
            elif content_raw != "":
                revealed_objs.append(RevealedObj(content_raw, "raw"))
            return revealed_objs
        else:
            raise FileNotFoundError(path)

    def _reveal_file(self, filename):
        """
        detects filename by extension (.yml/.yaml, .json or otherwise raw)
        reveals secrets in content
        """
        if filename.endswith(".yml") or filename.endswith(".yaml"):
            logger.debug("Revealer: revealing yml file: %s", filename)
            with open(filename) as fp:
                obj = [o for o in yaml.load_all(fp, Loader=YamlLoader)]
                rev_obj = self.reveal_obj(obj)
                return (
                    yaml.dump_all(
                        rev_obj,
                        Dumper=PrettyDumper,
                        default_flow_style=False,
                        explicit_start=True,
                    ),
                    "yaml",
                )
        elif filename.endswith(".json"):
            logger.debug("Revealer: revealing json file: %s", filename)
            with open(filename) as fp:
                obj = json.load(fp)
                rev_obj = self.reveal_obj(obj)
                return json.dumps(rev_obj, indent=4, sort_keys=True), "json"
        else:
            logger.debug("Revealer: revealing raw file: %s", filename)
            return self.reveal_raw_file(filename), "raw"

    def _reveal_dir(self, dirname):
        """
        returns tuple with yaml, json, and raw concatenated output for revealed file types
        recurses through subdirectories in dirname
        """
        out_yaml = ""
        out_json = ""
        out_raw = ""

        # find yaml/json/raw files and concatenate output per type
        for fpath in list_all_paths(dirname):
            if not os.path.isfile(fpath):
                continue
            if fpath.endswith(".yml") or fpath.endswith(".yaml"):
                out, _ = self._reveal_file(fpath)
                out_yaml += out
            elif fpath.endswith(".json"):
                out, _ = self._reveal_file(fpath)
                out_json += out
            else:
                out, _ = self._reveal_file(fpath)
                out_raw += out

        return out_yaml, out_json, out_raw

    def _reveal_replace_match(self, match_obj):
        """returns decrypted value from tag in match_obj"""
        tag, _, _ = match_obj.groups()
        m = re.search(REF_TOKEN_SUBVAR_PATTERN, tag)

        if m is None:
            # if this is an embedded ref with subvar_path set
            # grab from controller
            ref = self.ref_controller[tag]
            if ref.embedded_subvar_path is not None:
                revealed_data = ref.reveal()
                # this should be yaml, decode, load and check
                revealed_yaml = yaml.load(revealed_data, Loader=YamlLoader)
                if not isinstance(revealed_yaml, dict):
                    raise RefError(
                        "Revealer: revealed secret is not in embedded yaml, "
                        "cannot access sub-variable at {}".format(ref.embedded_subvar_path)
                    )
                try:
                    logger.debug(
                        'Revealer: embedded sub-variable path "%s"' "matched in tag %s",
                        ref.embedded_subvar_path,
                        tag,
                    )
                    return self._get_value_in_yaml_path(revealed_yaml, ref.embedded_subvar_path)
                except KeyError:
                    raise RefError(
                        "Revealer: cannot access {} sub-variable key {}".format(tag, ref.embedded_subvar_path)
                    )

            # else this is just a ref
            else:
                logger.debug('Revealer: no sub-variable path was matched in "%s"', tag)
                return self._reveal_tag_without_subvar(tag)

        # this is a ref with subvar
        else:
            subvar_path = m.groups()
            # strip away the @
            subvar_path = subvar_path[0][1:]
            logger.debug('Revealer: sub-variable path "%s" matched in tag %s', subvar_path, tag)
            tag_without_yaml_path = re.sub(REF_TOKEN_SUBVAR_PATTERN, "", tag)
            plaintext = self._reveal_tag_without_subvar(tag_without_yaml_path)
            ref = self.ref_controller[tag_without_yaml_path]
            plaintext = base64.b64decode(plaintext).decode("utf-8") if ref.encoding == "base64" else plaintext
            revealed_yaml = yaml.load(plaintext, Loader=YamlLoader)
            if not isinstance(revealed_yaml, dict):
                raise RefError(
                    "Revealer: revealed secret is not in yaml, "
                    "cannot access {} sub-variable at {}".format(subvar_path, tag)
                )
            try:
                value = self._get_value_in_yaml_path(revealed_yaml, subvar_path)
                return base64.b64encode(value.encode("utf-8")) if ref.encoding == "base64" else value
            except KeyError:
                raise RefError("Revealer: cannot access {} sub-variable key {}".format(tag, subvar_path))

    @lru_cache(maxsize=256)
    def _reveal_tag_without_subvar(self, tag_without_subvar):
        ref = self.ref_controller[tag_without_subvar]
        logger.debug("Revealer: revealing tag %s for the first time", tag_without_subvar)
        return ref.reveal()

    def _get_value_in_yaml_path(self, d, yaml_path):
        """using the sub-variable path as nested keys, returns the value in the dictionary"""
        keys = yaml_path.split(".")
        value = d
        for key in keys:
            value = value[key]

        return value

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
                raise RefError("Could not find ref backend for tag: {}".format(tag))

        return compile_replace_match

    def reveal_raw_string(self, tag_string):
        return self.regex.sub(self._reveal_replace_match, tag_string)

    def reveal_raw_file(self, filename):
        """
        read filename and reveal content (per line search and replace) with refs
        set filename=None to read stdin
        returns string with revealed content
        """
        out_raw = ""
        if filename is None:
            for line in sys.stdin:
                revealed = self.reveal_raw_string(line)
                out_raw += revealed
        else:
            with open(filename) as fp:
                for line in fp:
                    revealed = self.reveal_raw_string(line)
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
    @contextmanager
    def detailedException(self, ref_key):
        try:
            yield
        except RefBackendError as e:
            raise RefBackendError(f"{e}\n  for key {ref_key}")

    def __init__(self, path, **kwargs):
        """
        gets and sets tags for ref type objects.
        auto registers backends
        """
        self.backends = {}
        self.path = path
        self.embed_refs = kwargs.get("embed_refs", False)

    def register_backend(self, backend):
        "register backend type"
        assert isinstance(backend, PlainRefBackend)
        self.backends[backend.type_name] = backend

    def _get_backend(self, type_name):
        "imports and registers backend according to type_name"
        try:
            return self.backends[type_name]
        except KeyError:
            ref_kwargs = {"embed_refs": self.embed_refs}
            if type_name == "plain":
                from kapitan.refs.base import PlainRefBackend

                # XXX embed_refs in plain backend does nothing
                self.register_backend(PlainRefBackend(self.path, **ref_kwargs))

            elif type_name == "env":
                from kapitan.refs.env import EnvRefBackend

                # embed_refs in env backend also does nothing
                self.register_backend(EnvRefBackend(self.path, **ref_kwargs))

            elif type_name == "base64":
                from kapitan.refs.base64 import Base64RefBackend

                self.register_backend(Base64RefBackend(self.path, **ref_kwargs))
            elif type_name == "gpg":
                from kapitan.refs.secrets.gpg import GPGBackend

                self.register_backend(GPGBackend(self.path, **ref_kwargs))
            elif type_name == "gkms":
                from kapitan.refs.secrets.gkms import GoogleKMSBackend

                self.register_backend(GoogleKMSBackend(self.path, **ref_kwargs))
            elif type_name == "awskms":
                from kapitan.refs.secrets.awskms import AWSKMSBackend

                self.register_backend(AWSKMSBackend(self.path, **ref_kwargs))
            elif type_name == "vaultkv":
                from kapitan.refs.secrets.vaultkv import VaultBackend

                self.register_backend(VaultBackend(self.path, **ref_kwargs))
            elif type_name == "vaulttransit":
                from kapitan.refs.secrets.vaulttransit import VaultBackend

                self.register_backend(VaultBackend(self.path, **ref_kwargs))
            elif type_name == "azkms":
                from kapitan.refs.secrets.azkms import AzureKMSBackend

                self.register_backend(AzureKMSBackend(self.path, **ref_kwargs))
            else:
                raise RefBackendError(f"no backend for ref type: {type_name}")
        return self.backends[type_name]

    def tag_type(self, tag):
        "returns ref type for tag"
        # ?{ref:my/secret/token} or ?{ref:my/secret/token||func:param1:param2} or ?{ref:my/secret/token:deadbeef}
        _, token, _ = self.tag_params(tag)
        return self.token_type(token)

    def tag_params(self, tag):
        "returns tag parameter tuple with (tag, token, func_str)"
        match = re.match(REF_TOKEN_TAG_PATTERN, tag)
        if match:
            tag, token, func_str = match.groups()
            return tag, token, func_str
        else:
            raise RefError(
                "{}: is not a valid tag".format(tag),
                "\ntry something like: ?{ref:path/to/secret||function:param1:param2}",
            )

    def token_type(self, token):
        "returns ref type for token"
        type_name = self.token_type_name(token)

        # force type_name to register
        self._get_backend(type_name)

        return self.backends[type_name].ref_type

    def token_type_name(self, token):
        "returns ref type name for token"
        attrs = token.split(":")
        type_name = attrs[0]

        return type_name

    def ref_from_embedded(self, type_name, b64_path):
        "returns ref from embedded (base64 and json) b64_path"
        # deserialise base64 and json data from b64_path
        json_data = base64.b64decode(b64_path).decode()
        json_data = json.loads(json_data)
        backend = self._get_backend(type_name)

        # strip useless keys
        json_data.pop("type")

        data = json_data.pop("data").encode()
        # create new ref with deserialised data and remaining keys as kwargs
        # note that encrypt=False is only for secret ref types, non secret refs (e.g. base64) will ignore
        # from_base64 is True because data is always base64 encoded in embedded form
        ref = backend.ref_type(data, encrypt=False, from_base64=True, **json_data)

        return ref

    def ref_from_ref_file(self, ref_file_path):
        "returns ref from a ref file_path"
        with open(ref_file_path, "r") as ref_file:
            ref_file_obj = yaml.safe_load(ref_file)

            type_name = ref_file_obj.pop("type")
            data = ref_file_obj.pop("data")

            backend = self._get_backend(type_name)

            # create new ref with deserialised data and remaining keys as kwargs
            # note that encrypt=False is only for secret ref types, non secret refs (e.g. base64) will ignore
            # from_base64 is True  because data is being loaded from a ref file where it is always base64
            ref = backend.ref_type(data, encrypt=False, from_base64=True, **ref_file_obj)
        return ref

    def _get_from_token(self, token):
        attrs = token.split(":")

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

            if hash == "embedded":
                return self.ref_from_embedded(type_name, path)
            else:
                backend = self._get_backend(type_name)
                ref = backend[path]
                if ref.hash[:8] == hash:
                    return ref
                else:
                    raise RefHashMismatchError(
                        "{}: token hash does not match with stored reference hash: {}".format(
                            token, ref.token
                        )
                    )
        else:
            return None

    def _set_to_token(self, token, ref_obj):
        attrs = token.split(":")

        if len(attrs) == 2:
            type_name = attrs[0]
            path = attrs[1]
            backend = self._get_backend(type_name)
            assert isinstance(ref_obj, backend.ref_type)
            backend[path] = ref_obj
        else:
            raise RefError(f"{token}: is not a valid token")

    def _eval_func_str(self, ctx, func_str):
        """
        evals and updates context ctx for func_str
        returns evaluated ctx
        """
        # parse functions
        assert func_str.startswith("||")
        funcs = func_str[2:].split("|")

        for func in funcs:
            # parse parameters for function
            func_name, *func_params = func.strip().split(":")
            if func_name == "base64":  # not a real function
                ctx.encode_base64 = True
            else:
                try:
                    # call function with parameters and set generated secret to ctx.data
                    eval_func(func_name, ctx, *func_params)
                except KeyError:
                    raise RefError(
                        "{}: unknown ref function used. Choose one of: {}".format(
                            func_name, [key for key in get_func_lookup()]
                        )
                    )
                except TypeError:
                    raise RefError("{}: too many arguments for function {}".format(func_params, func_name))

        return ctx

    def __getitem__(self, key):
        # ?{ref:my/secret/token} or ?{ref:my/secret/token||func:param1:param2} or ?{ref:my/secret/token:deadbeef}
        # e.g  ?{ref:basepayloadhere==:embedded} (for embedded refs)
        tag, token, func_str = self.tag_params(key)

        with self.detailedException(key):
            # if there is no function, grab token
            if func_str is None:
                ref = self._get_from_token(token)
                if ref:
                    return ref
            else:
                if re.search(REF_TOKEN_SUBVAR_PATTERN, token) is not None:
                    raise RefError("Ref: references with sub-variables must be created manually")
                # if there is a function, try grabbing token
                try:
                    ref = self._get_from_token(token)
                    if ref:
                        return ref
                except KeyError:
                    # if func is set and ref doesnt exist,
                    # raise RefFromFuncError to indicate new ref needs to be created
                    raise RefFromFuncError(
                        f"{token}: does not exist and must be created from function: {func_str}"
                    )

        raise KeyError(f"{tag}: ref not found")

    def __setitem__(self, key, value):
        # ?{ref:my/secret/token} or ?{ref:my/secret/token|func:param1:param2}
        tag, token, func_str = self.tag_params(key)

        with self.detailedException(key):
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
                    value.kwargs["encoding"] = "base64"
                    ref_obj = ref_type.from_params(b64_data, value)
                else:
                    ref_obj = ref_type.from_params(ctx.data, value)

                return self._set_to_token(token, ref_obj)


class FunctionContext(object):
    def __init__(self, data):
        "Carry context across function evaluation"
        self.data = data
