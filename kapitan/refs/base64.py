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

"base64 ref module"

import base64
import errno
import logging
import yaml

from kapitan.refs.base import PlainRef, PlainRefBackend

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader

logger = logging.getLogger(__name__)


class Base64Ref(PlainRef):
    def __init__(self, data, from_base64=False, **kwargs):
        """
        writes data
        set from_base64 to load already base64 encoded data
        """
        super().__init__(data, **kwargs)
        self.type_name = 'base64'
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

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        """
        return a new Base64Ref from file at ref_full_path
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

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {"data": self.data, "encoding": self.encoding,
                "type": self.type_name}


class Base64RefBackend(PlainRefBackend):
    def __init__(self, path, ref_type=Base64Ref):
        super().__init__(path, ref_type)
        self.type_name = 'base64'
