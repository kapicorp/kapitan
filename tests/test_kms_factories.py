#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Characterization of the KMS secret-handler accessors.

Pins the lazy-memoize contract of ``gkms_obj``/``awskms_obj``/``azkms_obj``:
the underlying cloud client is constructed once, the result is cached, and
subsequent calls return the same object without reconstructing. The planned
refactor replaces ``cached.*_obj`` globals with memoized factories — these
tests guard that the construct-once behavior survives that swap.
"""

import unittest
from unittest import mock

from kapitan import cached
from kapitan.refs.secrets.awskms import awskms_obj
from kapitan.refs.secrets.azkms import azkms_obj
from kapitan.refs.secrets.gkms import gkms_obj


class GkmsFactoryTest(unittest.TestCase):
    def setUp(self):
        cached.reset_cache()

    def tearDown(self):
        cached.reset_cache()

    @mock.patch("kapitan.refs.secrets.gkms.gcloud")
    def test_constructs_once_and_memoizes(self, gcloud):
        self.assertIsNone(cached.gkms_obj)

        first = gkms_obj()
        self.assertIsNotNone(first)
        self.assertIs(cached.gkms_obj, first)
        self.assertEqual(gcloud.build.call_count, 1)

        second = gkms_obj()
        self.assertIs(second, first)
        # still only built once — second call served from cache
        self.assertEqual(gcloud.build.call_count, 1)


class AwskmsFactoryTest(unittest.TestCase):
    def setUp(self):
        cached.reset_cache()

    def tearDown(self):
        cached.reset_cache()

    @mock.patch("kapitan.refs.secrets.awskms.boto3")
    def test_constructs_once_and_memoizes(self, boto3):
        self.assertIsNone(cached.awskms_obj)

        first = awskms_obj()
        self.assertIsNotNone(first)
        self.assertIs(cached.awskms_obj, first)
        self.assertEqual(boto3.session.Session.call_count, 1)

        second = awskms_obj()
        self.assertIs(second, first)
        self.assertEqual(boto3.session.Session.call_count, 1)


class AzkmsFactoryTest(unittest.TestCase):
    KEY_ID = "https://kapitanbackend.vault.azure.net/keys/myKey/deadbeef"

    def setUp(self):
        cached.reset_cache()

    def tearDown(self):
        cached.reset_cache()

    @mock.patch("kapitan.refs.secrets.azkms.CryptographyClient")
    @mock.patch("kapitan.refs.secrets.azkms.KeyClient")
    @mock.patch("kapitan.refs.secrets.azkms.DefaultAzureCredential")
    def test_constructs_once_and_memoizes(self, credential, key_client, crypto_client):
        self.assertIsNone(cached.azkms_obj)

        first = azkms_obj(self.KEY_ID)
        self.assertIsNotNone(first)
        self.assertIs(cached.azkms_obj, first)
        self.assertEqual(crypto_client.call_count, 1)

        second = azkms_obj(self.KEY_ID)
        self.assertIs(second, first)
        # memoized: CryptographyClient not constructed a second time
        self.assertEqual(crypto_client.call_count, 1)
