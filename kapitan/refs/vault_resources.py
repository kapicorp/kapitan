# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"hashicorp vault resource functions"

import os
import logging
import hvac

from kapitan.errors import KapitanError

logger = logging.getLogger(__name__)


class VaultError(KapitanError):
    """Generic vault errors"""

    pass


class VaultClient(hvac.Client):
    """client connects to vault server and authenticates itself"""

    def __init__(self, vault_parameters):
        self.vault_parameters = vault_parameters
        self.env = get_env(vault_parameters)

        super().__init__(**{k: v for k, v in self.env.items() if k != "auth"})

        self.authenticate()

    def get_auth_token(self):
        """
        get token either from environment or from file
        """
        auth_type = self.vault_parameters["auth"]
        token = ""

        if auth_type in ["token", "github"]:
            token = os.getenv("VAULT_TOKEN")
            if not token:
                token_file = os.path.join(os.path.expanduser("~"), ".vault-token")
                token = self.read_token_from_file(token_file)

        self.env["token"] = token

    def read_token_from_file(self, token_file):
        try:
            with open(token_file, "r") as fp:
                token = fp.read()
        except IOError:
            raise VaultError("Cannot read file {}".format(token_file))

        if not token:
            raise VaultError("{} is empty".format(token_file))

        return token

    def authenticate(self):
        # DIFFERENT LOGIN METHOD BASED ON AUTHENTICATION TYPE
        auth_type = self.vault_parameters["auth"]
        self.get_auth_token()
        username = os.getenv("VAULT_USERNAME")
        password = os.getenv("VAULT_PASSWORD")

        if auth_type == "token":
            self.token = self.env["token"]
        elif auth_type == "ldap":
            self.auth.ldap.login(username=username, password=password)
        elif auth_type == "userpass":
            self.auth.userpass.login(username=username, password=password)
        elif auth_type == "approle":
            self.auth.approle.login(os.getenv("VAULT_ROLE_ID"), secret_id=os.getenv("VAULT_SECRET_ID"))
        elif auth_type == "github":
            self.auth.github.login(token=self.env["token"])
        else:
            raise VaultError("Authentication type '{}' not supported".format(auth_type))

        if not self.is_authenticated():
            self.adapter.close()
            raise VaultError("Vault Authentication Error, Environment Variables defined?")


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
            ### ssl-cert-verification.
            See http://docs.python-requests.org/en/master/user/advanced/
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
                raise VaultError("Neither VAULT_CACERT nor VAULT_CAPATH specified")
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
