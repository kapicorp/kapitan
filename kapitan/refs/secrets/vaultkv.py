# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"hashicorp vault kv secrets module"

import base64
import logging
import os
from binascii import Error as b_error
from sys import exit

from kapitan import cached
from kapitan.errors import KapitanError
from kapitan.refs.base import RefError
from kapitan.refs.base64 import Base64Ref, Base64RefBackend

import hvac
from hvac.exceptions import Forbidden, InvalidPath

logger = logging.getLogger(__name__)


class VaultError(KapitanError):
    """Generic vault errors"""

    pass


def get_env(parameter):
    """
    The following variables need to be exported to the environment or defined in inventory.
        * VAULT_ADDR: url for vault
        * VAULT_SKIP_VERIFY=true: if set, do not verify presented TLS certificate before communicating with Vault server.
        * VAULT_CLIENT_KEY: path to an unencrypted PEM-encoded private key matching the client certificate
        * VAULT_CLIENT_CERT: path to a PEM-encoded client certificate for TLS authentication to the Vault server
        * VAULT_CACERT: path to a PEM-encoded CA cert file to use to verify the Vault server TLS certificate
        * VAULT_CAPATH: path to a directory of PEM-encoded CA cert files to verify the Vault server TLS certificate
        * VAULT_NAMESPACE: specify the Vault Namespace, if you have one

    Following keys are used to creates a new hvac client instance.
        :param url: Base URL for the Vault instance being addressed.
        :type url: str
        :param cert: Certificates for use in requests sent to the Vault instance. This should be a tuple with the
            certificate and then key.
        :type cert: tuple
        :param verify: Either a boolean to indicate whether TLS verification should be performed when sending requests to Vault,
            or a string pointing at the CA bundle to use for verification.
            See http://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification.
        :type verify: Union[bool,str]
        :param namespace: Optional Vault Namespace.
        :type namespace: str
    """
    client_parameters = {}
    client_parameters["url"] = parameter.get("VAULT_ADDR", os.getenv("VAULT_ADDR", default=""))
    client_parameters["namespace"] = parameter.get(
        "VAULT_NAMESPACE", os.getenv("VAULT_NAMESPACE", default="")
    )
    # VERIFY VAULT SERVER TLS CERTIFICATE
    skip_verify = str(parameter.get("VAULT_SKIP_VERIFY", os.getenv("VAULT_SKIP_VERIFY", default="")))

    if skip_verify.lower() == "false":
        cert = parameter.get("VAULT_CACERT", os.getenv("VAULT_CACERT", default=""))
        if not cert:
            cert_path = parameter.get("VAULT_CAPATH", os.getenv("VAULT_CAPATH", default=""))
            if not cert_path:
                raise Exception("Neither VAULT_CACERT nor VAULT_CAPATH specified")
            client_parameters["verify"] = cert_path
        else:
            client_parameters["verify"] = cert
    else:
        client_parameters["verify"] = False

    # CLIENT CERTIFICATE FOR TLS AUTHENTICATION
    client_key = parameter.get("VAULT_CLIENT_KEY", os.getenv("VAULT_CLIENT_KEY", default=""))
    client_cert = parameter.get("VAULT_CLIENT_CERT", os.getenv("VAULT_CLIENT_CERT", default=""))
    if client_key != "" and client_cert != "":
        client_parameters["cert"] = (client_cert, client_key)
    return client_parameters


def vault_obj(vault_parameters):
    """
    vault_parameters: necessary parameters to authenticate & get value from vault, provided by inventory
    e.g.:
        auth: userpass
        VAULT_ADDR: http://127.0.0.1:8200
        VAULT_SKIP_VERIFY: false
    Authenticate client to server and return client object
    """
    env = get_env(vault_parameters)

    client = hvac.Client(**{k: v for k, v in env.items() if k != "auth"})

    auth_type = vault_parameters["auth"]
    # GET TOKEN EITHER FROM ENVIRONMENT OF FILE
    if auth_type in ["token", "github"]:
        env["token"] = os.getenv("VAULT_TOKEN")
        if not env["token"]:
            try:
                token_file = os.path.join(os.path.expanduser("~"), ".vault-token")
                with open(token_file, "r") as f:
                    env["token"] = f.read()
                if env["token"] == "":
                    raise VaultError("{file} is empty".format(file=token_file))
            except IOError:
                raise VaultError("Cannot read file {file}".format(file=token_file))
    # DIFFERENT LOGIN METHOD BASED ON AUTHENTICATION TYPE
    if auth_type == "token":
        client.token = env["token"]
    elif auth_type == "ldap":
        client.auth.ldap.login(username=os.getenv("VAULT_USERNAME"), password=os.getenv("VAULT_PASSWORD"))
    elif auth_type == "userpass":
        client.auth_userpass(username=os.getenv("VAULT_USERNAME"), password=os.getenv("VAULT_PASSWORD"))
    elif auth_type == "approle":
        client.auth_approle(os.getenv("VAULT_ROLE_ID"), secret_id=os.getenv("VAULT_SECRET_ID"))
    elif auth_type == "github":
        client.auth.github.login(token=env["token"])
    else:
        raise "Authentication type '{auth}' not supported".format(auth=auth_type)

    if client.is_authenticated():
        return client
    else:
        raise VaultError("Vault Authentication Error, Environment Variables defined?")


class VaultSecret(Base64Ref):
    """
    Hashicorp Vault support for KV Secret Engine
    """

    def __init__(self, data, vault_params, **kwargs):
        """
        Set vault parameter and encoding of data
        """
        self.data = data
        self.vault_params = vault_params
        super().__init__(self.data, **kwargs)
        self.type_name = "vaultkv"

    @classmethod
    def from_params(cls, data, ref_params):
        """
        Return new VaultSecret from data and ref_params: target_name
        parameters will be grabbed from the inventory via target_name
        """
        try:
            target_name = ref_params.kwargs["target_name"]
            if target_name is None:
                raise ValueError("target_name not set")

            target_inv = cached.inv["nodes"].get(target_name, None)
            if target_inv is None:
                raise ValueError("target_inv not set")

            ref_params.kwargs["vault_params"] = target_inv["parameters"]["kapitan"]["secrets"]["vaultkv"]
            return cls(data, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not create VaultSecret: vaultkv parameters missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, encrypt=False, **kwargs)

    def reveal(self):
        """
        Returns decrypted data
        """
        # can't use super().reveal() as we want bytes
        try:
            self.data = base64.b64decode(self.data, validate=True)
        except b_error:
            exit("non-alphabet characters in the data")

        return self._decrypt()

    def _decrypt(self):
        """
        Authenticate with Vault server & returns value of the key from secret

        :returns: secret in plain text
        """
        try:
            client = vault_obj(self.vault_params)
            # token will comprise of two parts path_in_vault:key
            data = self.data.decode("utf-8").rstrip().split(":")
            return_data = ""
            if self.vault_params.get("engine") == "kv":
                response = client.secrets.kv.v1.read_secret(
                    path=data[0], mount_point=self.vault_params.get("mount", "secret")
                )
                return_data = response["data"][data[1]]
            else:
                response = client.secrets.kv.v2.read_secret_version(
                    path=data[0], mount_point=self.vault_params.get("mount", "secret")
                )
                return_data = response["data"]["data"][data[1]]
            client.adapter.close()
        except Forbidden:
            raise VaultError(
                "Permission Denied. "
                + "make sure the token is authorised to access {path} on Vault".format(path=data[0])
            )
        except InvalidPath:
            raise VaultError("{path} does not exist on Vault secret".format(path=data[0]))

        if return_data == "":
            raise VaultError("'{key}' doesn't exist on '{path}'".format(key=data[1], path=data[0]))
        return return_data

    def dump(self):
        """
        Returns dict with keys/values to be serialised.
        """
        return {
            "data": self.data,
            "encoding": self.encoding,
            "type": self.type_name,
            "vault_params": self.vault_params,
        }


class VaultBackend(Base64RefBackend):
    def __init__(self, path, ref_type=VaultSecret, **ref_kwargs):
        "init VaultBackend ref backend type"
        super().__init__(path, ref_type, **ref_kwargs)
        self.type_name = "vaultkv"
