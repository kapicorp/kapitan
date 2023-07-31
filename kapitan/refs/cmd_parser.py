from __future__ import print_function

import base64
import logging
import mimetypes
import os
import re
import sys

from kapitan.errors import KapitanError, RefHashMismatchError, InventoryError, RefError
from kapitan.refs.base import PlainRef, RefController, Revealer
from kapitan.refs.base64 import Base64Ref
from kapitan.refs.env import EnvRef
from kapitan.refs.secrets.awskms import AWSKMSSecret
from kapitan.refs.secrets.azkms import AzureKMSSecret
from kapitan.refs.secrets.gkms import GoogleKMSSecret
from kapitan.refs.secrets.gpg import GPGSecret, lookup_fingerprints
from kapitan.refs.secrets.vaultkv import VaultSecret
from kapitan.refs.secrets.vaulttransit import VaultTransit
from kapitan.resources import get_inventory
from kapitan.utils import fatal_error, search_target_token_paths

logger = logging.getLogger(__name__)


def handle_refs_command(args):
    ref_controller = RefController(args.refs_path)

    if args.write is not None:
        ref_write(args, ref_controller)
    elif args.reveal:
        ref_reveal(args, ref_controller)
    elif args.update:
        secret_update(args, ref_controller)
    elif args.update_targets or args.validate_targets:
        secret_update_validate(args, ref_controller)


def ref_write(args, ref_controller):
    "Write ref to ref_controller based on cli args"
    token_name = args.write
    file_name = args.file
    is_binary = args.binary
    data = None

    if file_name is None:
        fatal_error("--file is required with --write")
    if file_name == "-":
        data = ""
        for line in sys.stdin:
            data += line
    else:
        mime_type = mimetypes.guess_type(file_name)
        modifier = "rb" if is_binary else "r"
        with open(file_name, modifier) as fp:
            try:
                data = fp.read()
            except UnicodeDecodeError as e:
                raise KapitanError(
                    "Could not read file. Please add '--binary' if the file contains binary data. ({})".format(
                        e
                    )
                )

    if token_name.startswith("gpg:"):
        type_name, token_path = token_name.split(":")
        recipients = [dict((("name", name),)) for name in args.recipients]
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError(
                    "parameters.kapitan.secrets not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
            try:
                recipients = kap_inv_params["secrets"]["gpg"]["recipients"]

            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.gpg.recipients not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if not recipients:
            raise KapitanError(
                "No GPG recipients specified. Use --recipients or specify them in "
                + "parameters.kapitan.secrets.gpg.recipients and use --target-name"
            )
        secret_obj = GPGSecret(data, recipients, encode_base64=args.base64)
        tag = "?{{gpg:{}}}".format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("gkms:"):
        type_name, token_path = token_name.split(":")
        key = args.key
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError(
                    "parameters.kapitan.secrets not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
            try:
                key = kap_inv_params["secrets"]["gkms"]["key"]
            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.gkms.key not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.gkms.key and use --target-name"
            )
        secret_obj = GoogleKMSSecret(data, key, encode_base64=args.base64)
        tag = "?{{gkms:{}}}".format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("awskms:"):
        type_name, token_path = token_name.split(":")
        key = args.key
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError(
                    "parameters.kapitan.secrets not defined in inventory of target {}".format(
                        args.target_name
                    )
                )

            try:
                key = kap_inv_params["secrets"]["awskms"]["key"]
            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.awskms.key not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.awskms.key and use --target-name"
            )
        secret_obj = AWSKMSSecret(data, key, encode_base64=args.base64)
        tag = "?{{awskms:{}}}".format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("azkms:"):
        type_name, token_path = token_name.split(":")
        key = args.key
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError(
                    "parameters.kapitan.secrets not defined in inventory of target {}".format(
                        args.target_name
                    )
                )

            try:
                key = kap_inv_params["secrets"]["azkms"]["key"]
            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.azkms.key not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.azkms.key and use --target-name"
            )
        secret_obj = AzureKMSSecret(data, key, encode_base64=args.base64)
        tag = "?{{azkms:{}}}".format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("base64:"):
        type_name, token_path = token_name.split(":")
        _data = data if is_binary else data.encode()
        encoding = "original"
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = "base64"
        ref_obj = Base64Ref(_data, encoding=encoding)
        tag = "?{{base64:{}}}".format(token_path)
        ref_controller[tag] = ref_obj

    # VAULT Key-Value Engine
    elif token_name.startswith("vaultkv:"):
        type_name, token_path = token_name.split(":")
        _data = data if is_binary else data.encode()
        vault_params = {}
        encoding = "original"
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError(
                    "parameters.kapitan.secrets not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
            try:
                vault_params = kap_inv_params["secrets"]["vaultkv"]
            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.vaultkv not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if args.vault_auth:
            vault_params["auth"] = args.vault_auth
        if vault_params.get("auth") is None:
            raise KapitanError(
                "No Authentication type parameter specified. Specify it"
                " in parameters.kapitan.secrets.vaultkv.auth and use --target-name or use --vault-auth"
            )

        kwargs = {}

        # set mount
        mount = args.vault_mount
        if not mount:
            mount = vault_params.get("mount", "secret")  # secret is default mount point
        kwargs["mount_in_vault"] = mount

        # set path in vault
        path_in_vault = args.vault_path
        if not path_in_vault:
            path_in_vault = token_path  # token path in kapitan as default
        kwargs["path_in_vault"] = path_in_vault

        # set key
        key = args.vault_key
        if key:
            kwargs["key_in_vault"] = key
        else:
            raise RefError("Could not create VaultSecret: vaultkv: key is missing")

        secret_obj = VaultSecret(_data, vault_params, **kwargs)
        tag = "?{{vaultkv:{}}}".format(token_path)
        ref_controller[tag] = secret_obj

    # VAULT Transit engine
    elif token_name.startswith("vaulttransit:"):
        type_name, token_path = token_name.split(":")
        _data = data.encode()
        vault_params = {}
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            try:
                vault_params = kap_inv_params["secrets"]["vaulttransit"]
            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.vaulttransit not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if args.vault_auth:
            vault_params["auth"] = args.vault_auth
        if vault_params.get("auth") is None:
            raise KapitanError(
                "No Authentication type parameter specified. Specify it"
                " in parameters.kapitan.secrets.vaulttransit.auth and use --target-name or use --vault-auth"
            )

        secret_obj = VaultTransit(_data, vault_params)
        tag = "?{{vaulttransit:{}}}".format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("plain:"):
        type_name, token_path = token_name.split(":")
        _data = data if is_binary else data.encode()
        encoding = "original"
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = "base64"
        ref_obj = PlainRef(_data, encoding=encoding)
        tag = "?{{plain:{}}}".format(token_path)
        ref_controller[tag] = ref_obj

    elif token_name.startswith("env:"):
        type_name, token_path = token_name.split(":")
        _data = data if is_binary else data.encode()
        encoding = "original"
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = "base64"
        ref_obj = EnvRef(_data, encoding=encoding)
        tag = "?{{env:{}}}".format(token_path)
        ref_controller[tag] = ref_obj

    else:
        fatal_error(
            "Invalid token: {name}. Try using gpg/gkms/awskms/azkms/vaultkv/vaulttransit/base64/plain/env:{name}".format(
                name=token_name
            )
        )


def secret_update(args, ref_controller):
    "Update secret gpg recipients/gkms/awskms key"
    # TODO --update *might* mean something else for other types
    token_name = args.update
    if token_name.startswith("gpg:"):
        # args.recipients is a list, convert to recipients dict
        recipients = [
            dict(
                [
                    ("name", name),
                ]
            )
            for name in args.recipients
        ]
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            try:
                recipients = kap_inv_params["secrets"]["gpg"]["recipients"]

            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.gpg.recipients not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if not recipients:
            raise KapitanError(
                "No GPG recipients specified. Use --recipients or specify them in "
                + "parameters.kapitan.secrets.gpg.recipients and use --target"
            )
        type_name, token_path = token_name.split(":")
        tag = "?{{gpg:{}}}".format(token_path)
        secret_obj = ref_controller[tag]
        secret_obj.update_recipients(recipients)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("gkms:"):
        key = args.key
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            try:
                key = kap_inv_params["secrets"]["gkms"]["key"]
            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.gkms.key not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.gkms.key and use --target"
            )
        type_name, token_path = token_name.split(":")
        tag = "?{{gkms:{}}}".format(token_path)
        secret_obj = ref_controller[tag]
        secret_obj.update_key(key)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("azkms:"):
        key = args.key
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            try:
                key = kap_inv_params["secrets"]["azkms"]["key"]
            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.azkms.key not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.azkms.key and use --target"
            )
        type_name, token_path = token_name.split(":")
        tag = "?{{azkms:{}}}".format(token_path)
        secret_obj = ref_controller[tag]
        secret_obj.update_key(key)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("awskms:"):
        key = args.key
        if args.target_name:
            inv = get_inventory(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            try:
                key = kap_inv_params["secrets"]["awskms"]["key"]
            except KeyError:
                raise KapitanError(
                    "parameters.kapitan.secrets.awskms.key not defined in inventory of target {}".format(
                        args.target_name
                    )
                )
        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.awskms.key and use --target"
            )
        type_name, token_path = token_name.split(":")
        tag = "?{{awskms:{}}}".format(token_path)
        secret_obj = ref_controller[tag]
        secret_obj.update_key(key)
        ref_controller[tag] = secret_obj

    else:
        fatal_error("Invalid token: {name}. Try using gpg/gkms/awskms:{name}".format(name=token_name))


def ref_reveal(args, ref_controller):
    "Reveal secrets in file_name"
    revealer = Revealer(ref_controller)
    file_name = args.file
    reffile_name = args.ref_file
    tag_name = args.tag

    if file_name is None and reffile_name is None and tag_name is None:
        fatal_error("--file or --ref-file is required with --reveal")
    try:
        if file_name == "-" or reffile_name == "-":
            out = revealer.reveal_raw_file(None)
            sys.stdout.write(out)
        elif file_name:
            for rev_obj in revealer.reveal_path(file_name):
                sys.stdout.write(rev_obj.content)
        elif reffile_name:
            ref = ref_controller.ref_from_ref_file(reffile_name)
            sys.stdout.write(ref.reveal())
        elif tag_name:
            out = revealer.reveal_raw_string(tag_name)
            sys.stdout.write(out)
    except (RefHashMismatchError, KeyError):
        raise KapitanError("Reveal failed for file {name}".format(name=file_name))


def secret_update_validate(args, ref_controller):
    "Validate and/or update target secrets"
    # update gpg recipients/gkms/awskms key for all secrets in secrets_path
    # use --refs-path to set scanning path
    inv = inventory_reclass(args.inventory_path)
    targets = list(inv["nodes"].keys())
    refs_path = os.path.abspath(args.refs_path)
    target_token_paths = search_target_token_paths(refs_path, targets)
    ret_code = 0

    for target_name, token_paths in target_token_paths.items():
        kapitan_params = inv["nodes"][target_name]["parameters"]["kapitan"]
        secret_params = kapitan_params.get("secrets")
        if not secret_params:
            logger.error(f"{target_name}: missing key parameters.kapitan.secrets")
            raise InventoryError()

        backend_details_cache = {}

        for token_path in token_paths:
            # get ref backend type
            match = re.match(r"\?{(\w+):.+}", token_path)
            backend = match.group(0)

            if backend not in ("gpg", "gkms", "azkms", "awskms", "vaultkv", "vaulttransit"):
                logger.info(f"Invalid secret {backend}, could not get type, skipping {token_path}")
                continue

            backend_details = backend_details_cache.get(backend)
            if not backend_details:
                # get key from inventory
                backend_params = secret_params.get(backend)
                if not backend_params:
                    logger.error(f"{target_name}: missing key parameters.kapitan.secrets.{backend}")
                    raise InventoryError()

                key = "key"
                if backend == "gpg":
                    key = "recipients"
                elif backend == "vaultkv":
                    key = "auth"

                backend_details = backend_params.get(key)
                if not backend_details:
                    logger.debug(f"{target_name}: missing {backend} {key}, skipping {token_path}")
                    continue

                backend_details_cache[backend] = backend_details

            ref_obj = ref_controller[token_path]

            ref_details
            # backend custom behavior (refactoring possible)
            if backend == "gpg":
                backend_details = [{"fingerprint": f} for f in set(lookup_fingerprints(backend_details))]
                ref_details = [{"fingerprint": f} for f in set(lookup_fingerprints(ref_obj.recipients))]
            if backend == "vaulttransit":
                ref_details = ref_obj.vault_params["key"]
            else:
                ref_details = ref_obj.key

            # check for mismatches
            if backend_details != ref_details:
                if args.validate_targets:
                    logger.info(f"{token_path} {key} mismatch")
                    ret_code = 1
                else:
                    ref_obj.update_key(backend_details)
                    ref_controller[token_path] = ref_obj

    sys.exit(ret_code)
