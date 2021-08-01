# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"gpg secrets module"

import base64
import logging
import time

import gnupg
from kapitan import cached
from kapitan.errors import KapitanError
from kapitan.refs.base import RefError
from kapitan.refs.base64 import Base64Ref, Base64RefBackend

logger = logging.getLogger(__name__)


# XXX only use this for testing!
# pass custom kwargs to gpg encrypt()/decrypt()
GPG_KWARGS = {}

# XXX only use this for testing!
# pass custom fingerprints within from_params()
GPG_TARGET_FINGERPRINTS = {}


class GPGError(Exception):
    """Generic GPG errors"""

    pass


def gpg_obj(*args, **kwargs):
    if not cached.gpg_obj:
        cached.gpg_obj = gnupg.GPG(*args, **kwargs)
    return cached.gpg_obj


class GPGSecret(Base64Ref):
    def __init__(self, data, recipients, encrypt=True, encode_base64=False, **kwargs):
        """
        encrypts data for recipients
        set encode_base64 to True to base64 encode data before encrypting and writing
        set encrypt to False if loading data that is already encrypted and base64
        if fingerprint key is not set in recipients, the first non-expired fingerprint will be used
        if fingerprint is set, there will be no name based lookup
        """
        fingerprints = lookup_fingerprints(recipients)
        if encrypt:
            self._encrypt(data, fingerprints, encode_base64)
            if encode_base64:
                kwargs["encoding"] = "base64"
        else:
            self.data = data
            self.recipients = [{"fingerprint": f} for f in fingerprints]  # TODO move to .load() method
        super().__init__(self.data, **kwargs)
        self.type_name = "gpg"

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new GPPSecret from data and ref_params: target_name
        recipients will be grabbed from the inventory via target_name
        """
        try:
            # XXX only used for testing
            if GPG_TARGET_FINGERPRINTS:
                _fingerprints = [{"fingerprint": v} for _, v in GPG_TARGET_FINGERPRINTS.items()]
                return cls(data, _fingerprints, **ref_params.kwargs)

            target_name = ref_params.kwargs["target_name"]
            if target_name is None:
                raise ValueError("target_name not set")

            target_inv = cached.inv["nodes"].get(target_name, None)
            if target_inv is None:
                raise ValueError("target_inv not set")

            if "secrets" not in target_inv["parameters"]["kapitan"]:
                raise KapitanError(
                    f"parameters.kapitan.secrets not defined in inventory of target {target_name}"
                )

            recipients = target_inv["parameters"]["kapitan"]["secrets"]["gpg"]["recipients"]

            return cls(data, recipients, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not create GPGSecret: target_name missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, encrypt=False, **kwargs)

    def reveal(self):
        """
        returns decrypted data
        raises GPGError if decryption fails
        """
        # can't use super().reveal() as we want bytes
        ref_data = base64.b64decode(self.data)
        return self._decrypt(ref_data)

    def update_recipients(self, recipients):
        """
        re-encrypts data with new recipients, respects original encoding
        returns True if recipients are different and secret is updated, False otherwise
        """
        fingerprints = lookup_fingerprints(recipients)
        if set(fingerprints) == set([r["fingerprint"] for r in self.recipients]):
            return False

        data_dec = self.reveal()
        encode_base64 = self.encoding == "base64"
        if encode_base64:
            data_dec = base64.b64decode(data_dec).decode()
        self._encrypt(data_dec, fingerprints, encode_base64)
        self.data = base64.b64encode(self.data).decode()
        return True

    def _encrypt(self, data, fingerprints, encode_base64):
        """
        encrypts data
        set encode_base64 to True to base64 encode data before writing
        """
        assert isinstance(fingerprints, list)
        _data = data
        self.encoding = "original"
        if encode_base64:
            _data = base64.b64encode(data.encode())
            self.encoding = "base64"
        enc = gpg_obj().encrypt(_data, fingerprints, sign=True, armor=False, **GPG_KWARGS)
        if enc.ok:
            self.data = enc.data
            self.recipients = [{"fingerprint": f} for f in fingerprints]
        else:
            raise GPGError(enc.status)

    def _decrypt(self, data):
        """decrypt data"""
        dec = gpg_obj().decrypt(data, **GPG_KWARGS)
        if dec.ok:
            return dec.data.decode()
        else:
            raise GPGError(dec.status)

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {
            "data": self.data,
            "encoding": self.encoding,
            "recipients": self.recipients,
            "type": self.type_name,
        }


class GPGBackend(Base64RefBackend):
    def __init__(self, path, ref_type=GPGSecret, **ref_kwargs):
        "init GPGBackend ref backend type"
        super().__init__(path, ref_type, **ref_kwargs)
        self.type_name = "gpg"


def lookup_fingerprints(recipients):
    """returns a list of fingerprints for recipients obj"""
    lookedup = []
    for recipient in recipients:
        fingerprint = recipient.get("fingerprint")
        name = recipient.get("name")
        if fingerprint is None:
            lookedup_fingerprint = fingerprint_non_expired(name)
            lookedup.append(lookedup_fingerprint)
        else:
            # If fingerprint already set, don't lookup and reuse
            lookedup.append(fingerprint)

    # Remove duplicates, sort and return fingerprints list
    return sorted(set(lookedup))


def fingerprint_non_expired(recipient_name):
    """returns first non-expired key fingerprint for recipient_name"""
    try:
        keys = gpg_obj().list_keys(keys=(recipient_name,))
        for key in keys:
            if "expires" not in key:
                logger.info(
                    "Invalid dictionary structure for key for recipient: %s with fingerprint: %s",
                    recipient_name,
                    key["fingerprint"],
                )
                continue

            # if 'expires' is indefinite (meaning it is an empty string) OR
            # if 'expires' key is set and time is in the future, return
            if (not key["expires"]) or (time.time() < int(key["expires"])):
                return key["fingerprint"]
            else:
                logger.debug(
                    "Key for recipient: %s with fingerprint: %s has expired, skipping",
                    recipient_name,
                    key["fingerprint"],
                )
        raise GPGError(f"Could not find valid key for recipient: {recipient_name}")
    except IndexError as iexp:
        raise iexp
