# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"hashicorp vault resource functions"

import docker
import os
import logging

from time import sleep
from kapitan.errors import KapitanError

import hvac

logger = logging.getLogger(__name__)


class VaultServerError(KapitanError):
    """Generic vaultserver errors"""

    pass


class VaultServer:
    """Opens a vault server in a container"""

    def __init__(self):
        self.parameters = {}
        self.vault_url = None
        self.root_token = None
        self.vault_client = None
        self.docker_client = docker.from_env()
        self.vault_container = self.setup_container()
        self.setup_vault()

    def setup_container(self):
        env = {
            "VAULT_LOCAL_CONFIG": '{"backend": {"file": {"path": "/vault/file"}}, "listener":{"tcp":{"address":"0.0.0.0:8200","tls_disable":"true"}}}'
        }
        vault_container = self.docker_client.containers.run(
            image="hashicorp/vault",
            cap_add=["IPC_LOCK"],
            ports={"8200/tcp": ("127.0.0.1", None)},
            environment=env,
            detach=True,
            auto_remove=True,
            command="server",
        )

        # make sure the container is up & running before testing

        while vault_container.status != "running":
            sleep(2)
            vault_container.reload()

        port = vault_container.attrs["NetworkSettings"]["Ports"]["8200/tcp"][0]["HostPort"]
        host_ip = vault_container.attrs["NetworkSettings"]["Ports"]["8200/tcp"][0]["HostIp"]
        self.vault_url = f"http://{host_ip}:{port}"
        self.parameters["VAULT_ADDR"] = self.vault_url
        logger.info(vault_container.attrs["NetworkSettings"]["Ports"]["8200/tcp"][0])
        logger.info(f"Vault container is up and running on url {self.vault_url}")
        return vault_container

    def setup_vault(self):
        vault_status = {}
        while vault_status.get("initialized", False) == False:
            sleep(2)
            try:
                vault_status = self.initialise_vault()
                logger.info(f"status is {vault_status}")
            except Exception as e:
                logger.info(f"Exception is {e}")
                logger.info(f"status is {vault_status}")

        self.set_backend_path()
        self.set_vault_attributes()

    def initialise_vault(self):
        # Initialize vault, unseal, mount secret engine & add auth
        logger.info(f"Initialising vault on {self.vault_url}")
        vault_client = hvac.Client(url=self.vault_url)
        init = vault_client.sys.initialize()
        vault_client.sys.submit_unseal_keys(init["keys"])
        self.root_token = init["root_token"]
        vault_status = vault_client.sys.read_health_status(method="GET")
        vault_client.adapter.close()
        return vault_status

    def set_backend_path(self):
        logger.info("Setting backend path")
        self.vault_client = hvac.Client(url=self.vault_url, token=self.root_token)
        self.vault_client.sys.enable_secrets_engine(backend_type="kv-v2", path="secret")

    def get_policy(self):
        test_policy = """
            path "secret/*" {
            capabilities = ["read", "list", "create", "update"]
            }
        """
        return test_policy

    def set_vault_attributes(self):
        logger.info("Setting vault attributes")
        policy = "test_policy"
        test_policy = self.get_policy()
        self.vault_client.sys.create_or_update_policy(name=policy, policy=test_policy)
        os.environ["VAULT_USERNAME"] = "test_user"
        os.environ["VAULT_PASSWORD"] = "test_password"
        self.vault_client.sys.enable_auth_method("userpass")
        self.vault_client.auth.userpass.create_or_update_user(
            username="test_user", password="test_password", policies=[policy]
        )
        self.vault_client.sys.enable_auth_method("approle")
        self.vault_client.auth.approle.create_or_update_approle("test_role")
        os.environ["VAULT_ROLE_ID"] = self.vault_client.auth.approle.read_role_id("test_role")["data"][
            "role_id"
        ]
        os.environ["VAULT_SECRET_ID"] = self.vault_client.auth.approle.generate_secret_id("test_role")[
            "data"
        ]["secret_id"]
        os.environ["VAULT_TOKEN"] = self.vault_client.auth.token.create(policies=[policy], ttl="1h")["auth"][
            "client_token"
        ]

    def close_container(self):
        logger.info(f"Closing vault container {self.vault_url}")
        self.vault_client.adapter.close()

        self.vault_container.stop()
        self.docker_client.close()


class VaultTransitServer(VaultServer):
    def set_backend_path(self):
        self.vault_client = hvac.Client(url=self.vault_url, token=self.root_token)
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
