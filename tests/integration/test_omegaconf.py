# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging

from kapitan.inventory import get_inventory_backend


logger = logging.getLogger(__name__)


def test_load_and_resolve_single_target(migrated_omegaconf_inventory):
    target_name = "minikube"
    target_kapitan_metadata = {
        "_kapitan_": {
            "name": {
                "short": "minikube",
                "full": "minikube",
                "path": "minikube-es",
                "parts": ["minikube"],
            }
        }
    }

    inventory_backend = get_inventory_backend("omegaconf")
    inventory = inventory_backend(
        inventory_path=migrated_omegaconf_inventory, initialise=False
    )

    target = inventory.target_class(name=target_name, path="minikube-es.yml")
    logger.error("Loading target %s from %s", target_name, target.path)
    logger.error(target.parameters)
    inventory.targets.update({target_name: target})

    inventory.load_target(target)

    metadata = target.parameters.model_dump(by_alias=True)["_kapitan_"]
    assert metadata == target_kapitan_metadata["_kapitan_"]
    assert metadata["name"]["short"] == "minikube"
    assert target.parameters.target_name == "minikube-es"
    assert target.parameters.kubectl["insecure_skip_tls_verify"] is False
