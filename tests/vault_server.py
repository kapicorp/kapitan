# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"hashicorp vault resource functions"

import docker
import os
import shutil
import tempfile
import logging

import socket
from contextlib import closing
from time import sleep
from kapitan.errors import KapitanError

import hvac

logger = logging.getLogger(__name__)


class VaultServerError(KapitanError):
    """Generic vaultserver errors"""

    pass


class VaultServer:
    def __init__(self, ref_path, name=None):
        self.docker_client = docker.from_env()
        self.socket, self.port = self.find_free_port()
        self.container = self.setup_container(name)

        self.ref_path = ref_path
        self.vault_client = None
        self.setup_vault()

    def setup_container(self, name=None):
        env = {
            "VAULT_LOCAL_CONFIG": '{"backend": {"file": {"path": "/vault/file"}}, "listener":{"tcp":{"address":"0.0.0.0:8200","tls_disable":"true"}}}'
        }
        vault_container = self.docker_client.containers.run(
            image="vault",
            cap_add=["IPC_LOCK"],
            ports={"8200": self.port},
            environment=env,
            detach=True,
            remove=True,
            command="server",
            name=name,
        )
        # make sure the container is up & running before testing
        while vault_container.status != "running":
            sleep(2)
            vault_container.reload()

        return vault_container

    def find_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s, s.getsockname()[1]

    def setup_vault(self):
        init = self.prepare_vault()
        self.set_backend_path(init)
        self.set_vault_attributes()

    def prepare_vault(self):
        # Initialize vault, unseal, mount secret engine & add auth
        os.environ["VAULT_ADDR"] = f"http://127.0.0.1:{self.port}"
        self.vault_client = hvac.Client()
        init = self.vault_client.sys.initialize()
        self.vault_client.sys.submit_unseal_keys(init["keys"])
        os.environ["VAULT_ROOT_TOKEN"] = init["root_token"]
        self.vault_client.adapter.close()
        return init

    def set_backend_path(self, init):
        self.vault_client = hvac.Client(token=init["root_token"])
        self.vault_client.sys.enable_secrets_engine(backend_type="kv-v2", path="secret")

    def get_policy(self):
        test_policy = """
            path "secret/*" {
            capabilities = ["read", "list", "create", "update"]
            }
        """
        return test_policy

    def set_vault_attributes(self):
        policy = "test_policy"
        test_policy = self.get_policy()
        self.vault_client.sys.create_or_update_policy(name=policy, policy=test_policy)
        os.environ["VAULT_USERNAME"] = "test_user"
        os.environ["VAULT_PASSWORD"] = "test_password"
        self.vault_client.sys.enable_auth_method("userpass")
        self.vault_client.create_userpass(username="test_user", password="test_password", policies=[policy])
        self.vault_client.sys.enable_auth_method("approle")
        self.vault_client.create_role("test_role")
        os.environ["VAULT_ROLE_ID"] = self.vault_client.get_role_id("test_role")
        os.environ["VAULT_SECRET_ID"] = self.vault_client.create_role_secret_id("test_role")["data"][
            "secret_id"
        ]
        os.environ["VAULT_TOKEN"] = self.vault_client.create_token(policies=[policy], lease="1h")["auth"][
            "client_token"
        ]

    def close_container(self):
        self.vault_client.adapter.close()

        self.container.stop()
        self.docker_client.close()
        self.socket.close()

        shutil.rmtree(self.ref_path, ignore_errors=True)
        for i in ["ROOT_TOKEN", "TOKEN", "USERNAME", "PASSWORD", "ROLE_ID", "SECRET_ID"]:
            del os.environ["VAULT_" + i]


class VaultTransitServer(VaultServer):
    def set_backend_path(self, init):
        self.vault_client = hvac.Client(token=init["root_token"])
        self.vault_client.sys.enable_secrets_engine(backend_type="transit", path="transit")

    def get_policy(self):
        test_policy = """
        path "transit/encrypt/*" {
            capabilities = [ "create", "update" ]
        }

        path "transit/decrypt/*" {
            capabilities = [ "create", "update" ]
        }
        """
        return test_policy
