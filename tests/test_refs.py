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

"refs tests"

import tempfile
import unittest
from kapitan.refs.base import Ref, RefController, RefParams, Revealer
from kapitan.errors import RefFromFuncError, RefHashMismatchError

REFS_HOME = tempfile.mkdtemp()
REF_CONTROLLER = RefController(REFS_HOME)
REVEALER = Revealer(REF_CONTROLLER)


class RefsTest(unittest.TestCase):
    "Test refs"

    def test_ref_compile(self):
        "check ref compile() output is valid"
        tag = '?{ref:my/ref1}'
        REF_CONTROLLER[tag] = Ref(b'ref 1 data')
        ref_obj = REF_CONTROLLER[tag]
        compiled = ref_obj.compile()
        self.assertEqual(compiled, '?{ref:my/ref1:3342a45c}')

    def test_ref_recompile(self):
        "check ref recompile() output is valid"
        tag = '?{ref:my/ref1}'
        ref_obj = REF_CONTROLLER[tag]
        compiled = ref_obj.compile()
        self.assertEqual(compiled, '?{ref:my/ref1:3342a45c}')

    def test_ref_update_compile(self):
        "check ref update and compile() output is valid"
        tag = '?{ref:my/ref1}'
        REF_CONTROLLER[tag] = Ref(b'ref 1 more data')
        ref_obj = REF_CONTROLLER[tag]
        compiled = ref_obj.compile()
        self.assertEqual(compiled, '?{ref:my/ref1:ed438a62}')

    def test_ref_reveal(self):
        "check ref reveal() output is valid"
        tag = '?{ref:my/ref2}'
        REF_CONTROLLER[tag] = Ref(b'ref 2 data')
        ref_obj = REF_CONTROLLER[tag]
        revealed = ref_obj.reveal()
        self.assertEqual(revealed, 'ref 2 data')

    def test_ref_non_existent_raises_KeyError(self):
        "check RefController raises KeyError for non existent Ref"
        tag = '?{ref:non/existent}'
        with self.assertRaises(KeyError):
            REF_CONTROLLER[tag]

    def test_ref_tag_type(self):
        "check ref tag type is Ref"
        tag = '?{ref:my/ref3}'
        tag_type = REF_CONTROLLER.tag_type(tag)
        self.assertEqual(tag_type, Ref)

    def test_ref_tag_type_name(self):
        "check ref tag type name is ref"
        tag = '?{ref:my/ref4}'
        tag, token, func_str = REF_CONTROLLER.tag_params(tag)
        type_name = REF_CONTROLLER.token_type_name(token)
        self.assertEqual(tag, '?{ref:my/ref4}')
        self.assertEqual(token, 'ref:my/ref4')
        self.assertEqual(func_str, None)
        self.assertEqual(type_name, 'ref')

    def test_ref_tag_func_name(self):
        "check ref tag func name is correct"
        tag = '?{ref:my/ref5|randomstr}'
        tag, token, func_str = REF_CONTROLLER.tag_params(tag)
        self.assertEqual(tag, '?{ref:my/ref5|randomstr}')
        self.assertEqual(token, 'ref:my/ref5')
        self.assertEqual(func_str, '|randomstr')

    def test_ref_path(self):
        "check ref tag path is correct"
        tag = '?{ref:my/ref6}'
        tag, token, func_str = REF_CONTROLLER.tag_params(tag)
        self.assertEqual(tag, '?{ref:my/ref6}')
        self.assertEqual(token, 'ref:my/ref6')
        self.assertEqual(func_str, None)
        REF_CONTROLLER[tag] = Ref(b'ref 6 data')
        ref_obj = REF_CONTROLLER[tag]
        self.assertEqual(ref_obj.path, 'my/ref6')

    def test_ref_func_raise_RefFromFuncError(self):
        """
        check new ref tag with function raises RefFromFuncError
        and then creates it using RefParams()
        """
        tag = '?{ref:my/ref7|randomstr}'
        with self.assertRaises(RefFromFuncError):
            REF_CONTROLLER[tag]
        try:
            REF_CONTROLLER[tag]
        except RefFromFuncError:
            REF_CONTROLLER[tag] = RefParams()
        REF_CONTROLLER[tag]

    def test_ref_revealer_reveal_raw_data_tag(self):
        "check Revealer reveals raw data"
        tag = '?{ref:my/ref2}'
        data = "data with {}, period.".format(tag)
        revealed_data = REVEALER.reveal_raw(data)
        self.assertEqual(revealed_data, 'data with ref 2 data, period.')

    def test_ref_revealer_reveal_raw_data_tag_compiled_hash(self):
        "check Revealer reveals raw data with compiled tag (with hash)"
        tag = '?{ref:my/ref2}'
        tag_compiled = REF_CONTROLLER[tag].compile()
        data = "data with {}, period.".format(tag_compiled)
        revealed_data = REVEALER.reveal_raw(data)
        self.assertEqual(revealed_data, 'data with ref 2 data, period.')

    def test_ref_revealer_reveal_raw_data_tag_compiled_hash_mismatch(self):
        """
        check Revealer reveals raises RefHashMismatchError
        on mismatch compiled tag hashes
        """
        tag_compiled_hash_mismatch = '?{ref:my/ref2:deadbeef}'
        with self.assertRaises(RefHashMismatchError):
            data = "data with {}, period.".format(tag_compiled_hash_mismatch)
            REVEALER.reveal_raw(data)
