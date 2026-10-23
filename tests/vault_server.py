# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"hashicorp vault resource functions"

import logging
import os
from time import sleep

import hvac
from hvac.exceptions import InvalidRequest

from kapitan.errors import KapitanError


logger = logging.getLogger(__name__)


try:
    import docker
except ImportError:
    docker = None


class VaultServerError(KapitanError):
    """Generic vaultserver errors"""


# Module-level singletons so test classes can share vault server instances.
_shared_vault_servers = {}


def get_shared_vault_server(server_cls=None):
    """Return a shared VaultServer singleton, creating it if necessary."""
    cls = server_cls or VaultServer
    if cls not in _shared_vault_servers:
        _shared_vault_servers[cls] = cls()
    return _shared_vault_servers[cls]


class VaultServer:
    """Opens a vault server in a container or connects to an existing one."""

    def __init__(self):
        self.parameters = {}
        self.vault_url = None
        self.root_token = None
        self.vault_client = None
        self.dev_root_token = "root"
        self.docker_client = None
        self.vault_container = None
        # Credentials this server issues, scoped to its own policy. Stored on
        # the instance so they can be re-exported before each test (see
        # export_env): all servers share the same process environment, so a
        # token written by one would otherwise be clobbered by another.
        self.username = None
        self.password = None
        self.role_id = None
        self.secret_id = None
        self.token = None

        # If VAULT_ADDR is already set (e.g. CI service container), use it.
        existing_addr = os.environ.get("VAULT_ADDR")
        if existing_addr:
            self.vault_url = existing_addr
            self.parameters["addr"] = self.vault_url
            self.root_token = self.dev_root_token
            self.setup_vault()
        else:
            if docker is None:
                raise VaultServerError(
                    "Docker Python package is not installed. "
                    "Install it or set VAULT_ADDR to connect to an existing vault server."
                )
            self.docker_client = docker.from_env()
            self.vault_container = self.setup_container()
            self.setup_vault()

    def setup_container(self):
        env = {
            "SKIP_SETCAP": "1",
            "VAULT_DEV_ROOT_TOKEN_ID": self.dev_root_token,
            "VAULT_DEV_LISTEN_ADDRESS": "0.0.0.0:8200",
        }
        vault_container = self.docker_client.containers.run(
            image="hashicorp/vault",
            ports={"8200/tcp": ("127.0.0.1", None)},
            environment=env,
            cap_add=["IPC_LOCK"],
            detach=True,
            auto_remove=False,
            user="root",
            command="server -dev",
        )

        # make sure the container is up & running before testing

        while vault_container.status != "running":
            sleep(2)
            vault_container.reload()
            if vault_container.status in ("exited", "dead"):
                logs = vault_container.logs(tail=50).decode("utf-8", errors="replace")
                raise VaultServerError(
                    f"Vault container exited early: {vault_container.status}\n{logs}"
                )

        port = vault_container.attrs["NetworkSettings"]["Ports"]["8200/tcp"][0][
            "HostPort"
        ]
        host_ip = vault_container.attrs["NetworkSettings"]["Ports"]["8200/tcp"][0][
            "HostIp"
        ]
        self.vault_url = f"http://{host_ip}:{port}"
        self.parameters["addr"] = self.vault_url
        logger.info(vault_container.attrs["NetworkSettings"]["Ports"]["8200/tcp"][0])
        logger.info(f"Vault container is up and running on url {self.vault_url}")
        return vault_container

    def setup_vault(self):
        vault_status = {}
        while not vault_status.get("initialized", False):
            sleep(2)
            try:
                vault_client = hvac.Client(url=self.vault_url)
                vault_status = vault_client.sys.read_health_status(method="GET")
                vault_client.adapter.close()
                logger.info(f"status is {vault_status}")
            except Exception as e:
                logger.info(f"Exception is {e}")
                logger.info(f"status is {vault_status}")
                continue

            if not vault_status.get("initialized", False):
                try:
                    vault_status = self.initialise_vault()
                    logger.info(f"status is {vault_status}")
                except Exception as e:
                    logger.info(f"Exception is {e}")
                    logger.info(f"status is {vault_status}")
                    continue

        if not self.root_token:
            self.root_token = self.dev_root_token
        self.set_backend_path()
        self.set_vault_attributes()

    def initialise_vault(self):
        # Initialize vault, unseal, mount secret engine & add auth
        logger.info(f"Initialising vault on {self.vault_url}")
        vault_client = hvac.Client(url=self.vault_url)
        init = vault_client.sys.initialize(secret_threshold=3, secret_shares=5)
        vault_client.sys.submit_unseal_keys(init["keys"])
        self.root_token = init["root_token"]
        vault_status = vault_client.sys.read_health_status(method="GET")
        vault_client.adapter.close()
        return vault_status

    def set_backend_path(self):
        logger.info("Setting backend path")
        self.vault_client = hvac.Client(url=self.vault_url, token=self.root_token)
        try:
            self.vault_client.sys.enable_secrets_engine(
                backend_type="kv-v2", path="secret"
            )
        except InvalidRequest as exc:
            if "path is already in use" not in str(exc):
                raise

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
        self.username = "test_user"
        self.password = "test_password"
        try:
            self.vault_client.sys.enable_auth_method("userpass")
        except InvalidRequest as exc:
            if "path is already in use" not in str(exc):
                raise
        self.vault_client.auth.userpass.create_or_update_user(
            username=self.username, password=self.password, policies=[policy]
        )
        try:
            self.vault_client.sys.enable_auth_method("approle")
        except InvalidRequest as exc:
            if "path is already in use" not in str(exc):
                raise
        self.vault_client.auth.approle.create_or_update_approle("test_role")
        self.role_id = self.vault_client.auth.approle.read_role_id("test_role")["data"][
            "role_id"
        ]
        self.secret_id = self.vault_client.auth.approle.generate_secret_id("test_role")[
            "data"
        ]["secret_id"]
        self.token = self.vault_client.auth.token.create(policies=[policy], ttl="1h")[
            "auth"
        ]["client_token"]
        self.export_env()

    def export_env(self):
        """Export this server's credentials to the process environment.

        VaultClient reads VAULT_TOKEN (and the userpass/approle vars) from the
        environment, which is shared across all servers in a worker process.
        Tests run in parallel under pytest-xdist, so a single worker may set up
        more than one server (e.g. the kv and transit servers), each issuing a
        token scoped to a different policy. Whichever ran last would otherwise
        win globally and unrelated tests would fail with a permission error.
        Calling this from each test's setUp keeps the active credentials matched
        to the server under test.
        """
        os.environ["VAULT_USERNAME"] = self.username
        os.environ["VAULT_PASSWORD"] = self.password
        os.environ["VAULT_ROLE_ID"] = self.role_id
        os.environ["VAULT_SECRET_ID"] = self.secret_id
        os.environ["VAULT_TOKEN"] = self.token

    def close_container(self):
        logger.info(f"Closing vault container {self.vault_url}")
        if self.vault_client is not None:
            self.vault_client.adapter.close()

        if self.vault_container is not None:
            self.vault_container.stop()
            self.vault_container.remove()

        if self.docker_client is not None:
            self.docker_client.close()


class VaultTransitServer(VaultServer):
    def set_backend_path(self):
        self.vault_client = hvac.Client(url=self.vault_url, token=self.root_token)
        try:
            self.vault_client.sys.enable_secrets_engine(
                backend_type="transit", path="transit"
            )
        except InvalidRequest as exc:
            if "path is already in use" not in str(exc):
                raise

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
