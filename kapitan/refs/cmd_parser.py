from __future__ import print_function

import base64
import logging
import mimetypes
import os
import re
import sys

from kapitan.errors import KapitanError, RefError, RefHashMismatchError
from kapitan.inventory.model.references import (
    KapitanReferenceConfig,
    KapitanReferenceVaultKVConfig,
    KapitanReferenceVaultTransitConfig,
)
from kapitan.refs import KapitanReferencesTypes
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
        mimetypes.guess_type(file_name)
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

    # Empty configuration object
    reference_backend_configs = KapitanReferenceConfig()

    if args.target_name:
        inv = get_inventory(args.inventory_path)

        if not inv.get_parameters(args.target_name).kapitan.secrets:
            reference_backend_configs = inv.get_parameters(args.target_name).kapitan.secrets
            raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

    type_name, token_path = token_name.split(":")

    try:
        type_name = KapitanReferencesTypes(type_name)
    except ValueError:
        raise KapitanError(
            f"Invalid token type: {type_name}. Try using gpg/gkms/awskms/azkms/vaultkv/vaulttransit/base64/plain/env"
        )

    tag = f"?{{{type_name}:{token_path}}}"

    if type_name == KapitanReferencesTypes.GPG:
        # args.recipients is a list, convert to recipients dict
        recipients = [dict((("name", name),)) for name in args.recipients]

        if reference_backend_configs.gpg:
            recipients = reference_backend_configs.gpg.recipients

        if not recipients:
            raise KapitanError(
                "No GPG recipients specified. Use --recipients or specify them in "
                + "parameters.kapitan.secrets.gpg.recipients and use --target"
            )

        secret_obj = GPGSecret(data, recipients, encode_base64=args.base64)
        ref_controller[tag] = secret_obj

    elif type_name == KapitanReferencesTypes.GKMS:
        key = args.key

        if reference_backend_configs.gkms:
            key = reference_backend_configs.gkms.key

        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.gkms.key and use --target"
            )

        secret_obj = GoogleKMSSecret(data, key, encode_base64=args.base64)
        ref_controller[tag] = secret_obj

    elif type_name == KapitanReferencesTypes.AWSKMS:
        key = args.key

        if reference_backend_configs.awskms:
            key = reference_backend_configs.awskms.key

        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.awskms.key and use --target"
            )

        secret_obj = AWSKMSSecret(data, key, encode_base64=args.base64)
        ref_controller[tag] = secret_obj

    elif type_name == KapitanReferencesTypes.AZKMS:
        key = args.key

        if reference_backend_configs.azkms:
            key = reference_backend_configs.azkms.key

        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.azkms.key and use --target"
            )

        secret_obj = AzureKMSSecret(data, key, encode_base64=args.base64)
        ref_controller[tag] = secret_obj

    elif type_name == KapitanReferencesTypes.BASE64:
        _data = data if is_binary else data.encode()
        encoding = "original"
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = "base64"
        ref_obj = Base64Ref(_data, encoding=encoding)
        ref_controller[tag] = ref_obj

    # VAULT Key-Value Engine
    elif type_name == KapitanReferencesTypes.VAULTKV:
        _data = data if is_binary else data.encode()
        encoding = "original"

        vault_params = KapitanReferenceVaultKVConfig()

        if reference_backend_configs.vaultkv:
            vault_params = reference_backend_configs.vaultkv

        if args.vault_auth:
            vault_params.auth = args.vault_auth
        if not vault_params.auth:
            raise KapitanError(
                "No Authentication type parameter specified. Specify it"
                " in parameters.kapitan.secrets.vaultkv.auth and use --target-name or use --vault-auth"
            )

        kwargs = {}

        # set mount
        mount = args.vault_mount
        if vault_params.mount:
            mount = vault_params.mount

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
        ref_controller[tag] = secret_obj

    # VAULT Transit engine
    elif type_name == KapitanReferencesTypes.VAULTTRANSIT:
        _data = data.encode()
        vault_params = KapitanReferenceVaultTransitConfig()

        if reference_backend_configs.vaulttransit:
            vault_params = reference_backend_configs.vaulttransit

        if args.vault_auth:
            vault_params.auth = args.vault_auth

        if not vault_params.auth:
            raise KapitanError(
                "No Authentication type parameter specified. Specify it"
                " in parameters.kapitan.secrets.vaultkv.auth and use --target-name or use --vault-auth"
            )

        secret_obj = VaultTransit(_data, vault_params)
        ref_controller[tag] = secret_obj

    elif type_name == KapitanReferencesTypes.PLAIN:
        _data = data if is_binary else data.encode()
        encoding = "original"
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = "base64"
        ref_obj = PlainRef(_data, encoding=encoding)
        ref_controller[tag] = ref_obj

    elif type_name == KapitanReferencesTypes.ENV:
        _data = data if is_binary else data.encode()
        encoding = "original"
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = "base64"
        ref_obj = EnvRef(_data, encoding=encoding)
        ref_controller[tag] = ref_obj


def secret_update(args, ref_controller):
    "Update secret gpg recipients/gkms/awskms key"
    # TODO --update *might* mean something else for other types
    token_name = args.update
    reference_backend_configs = KapitanReferenceConfig()

    if args.target_name:
        inv = get_inventory(args.inventory_path)

        if not inv.get_parameters(args.target_name).kapitan.secrets:
            reference_backend_configs = inv.get_parameters(args.target_name).kapitan.secrets
            raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

    type_name, token_path = token_name.split(":")

    if type_name not in KapitanReferencesTypes:
        raise KapitanError(
            f"Invalid token type: {type_name}. Try using gpg/gkms/awskms/azkms/vaultkv/vaulttransit/base64/plain/env"
        )

    tag = f"?{{{type_name}:{token_path}}}"

    if type_name == KapitanReferencesTypes.GPG:
        # args.recipients is a list, convert to recipients dict
        recipients = [dict((("name", name),)) for name in args.recipients]

        if reference_backend_configs.gpg:
            recipients = reference_backend_configs.gpg.recipients

        if not recipients:
            raise KapitanError(
                "No GPG recipients specified. Use --recipients or specify them in "
                + "parameters.kapitan.secrets.gpg.recipients and use --target"
            )

        secret_obj = ref_controller[tag]
        secret_obj.update_recipients(recipients)
        ref_controller[tag] = secret_obj

    elif type_name == KapitanReferencesTypes.GKMS:
        key = args.key

        if reference_backend_configs.gkms:
            key = reference_backend_configs.gkms.key

        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.gkms.key and use --target"
            )
        secret_obj = ref_controller[tag]
        secret_obj.update_key(key)
        ref_controller[tag] = secret_obj

    elif type_name == KapitanReferencesTypes.AZKMS:
        key = args.key

        if reference_backend_configs.azkms:
            key = reference_backend_configs.azkms.key

        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.azkms.key and use --target"
            )
        secret_obj = ref_controller[tag]
        secret_obj.update_key(key)
        ref_controller[tag] = secret_obj

    elif type_name == KapitanReferencesTypes.AWSKMS:
        key = args.key

        if reference_backend_configs.awskms:
            key = reference_backend_configs.awskms.key

        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.awskms.key and use --target"
            )

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
    inv = get_inventory(args.inventory_path)
    targets = set(inv.targets.keys())
    secrets_path = os.path.abspath(args.refs_path)
    target_token_paths = search_target_token_paths(secrets_path, targets)
    ret_code = 0

    for target_name, token_paths in target_token_paths.items():
        secrets = inv.get_parameters(target_name).kapitan.secrets
        if not secrets:
            raise KapitanError("parameters.kapitan.secrets not defined in {}".format(target_name))

        for token_path in token_paths:
            type_name = re.match(r"\?\{(\w+):", token_path).group(1)
            if type_name == KapitanReferencesTypes.GPG:
                if not secrets.gpg:
                    logger.debug(
                        "secret_update_validate: target: %s has no inventory gpg recipients, skipping %s",
                        target_name,
                        token_path,
                    )
                    continue
                recipients = secrets.gpg.recipients
                secret_obj = ref_controller[token_path]
                target_fingerprints = set(lookup_fingerprints(recipients))
                secret_fingerprints = set(lookup_fingerprints(secret_obj.recipients))
                if target_fingerprints != secret_fingerprints:
                    if args.validate_targets:
                        logger.info("%s recipient mismatch", token_path)
                        to_remove = secret_fingerprints.difference(target_fingerprints)
                        to_add = target_fingerprints.difference(secret_fingerprints)
                        if to_remove:
                            logger.info("%s needs removal", to_remove)
                        if to_add:
                            logger.info("%s needs addition", to_add)
                        ret_code = 1
                    else:
                        new_recipients = [
                            dict(
                                [
                                    ("fingerprint", f),
                                ]
                            )
                            for f in target_fingerprints
                        ]
                        secret_obj.update_recipients(new_recipients)
                        ref_controller[token_path] = secret_obj

            elif type_name == KapitanReferencesTypes.GKMS:
                if not secrets.gkms:
                    logger.debug(
                        "secret_update_validate: target: %s has no inventory gkms key, skipping %s",
                        target_name,
                        token_path,
                    )
                    continue
                key = secrets.gkms.key
                secret_obj = ref_controller[token_path]
                if secrets.gpg.key != key:
                    if args.validate_targets:
                        logger.info("%s key mismatch", token_path)
                        ret_code = 1
                    else:
                        secret_obj.update_key(key)
                        ref_controller[token_path] = secret_obj

            elif type_name == KapitanReferencesTypes.VAULTTRANSIT:
                if not secrets.vaulttransit:
                    logger.debug(
                        "secret_update_validate: target: %s has no inventory vaulttransit key, skipping %s",
                        target_name,
                        token_path,
                    )
                    continue
                secret_obj = ref_controller[token_path]
                key = secrets.vaulttransit.key
                if key != secret_obj.vault_params["key"]:
                    if args.validate_targets:
                        logger.info("%s key mismatch", token_path)
                        ret_code = 1
                    else:
                        secret_obj.update_key(key)
                        ref_controller[token_path] = secret_obj

            elif type_name == KapitanReferencesTypes.AWSKMS:
                if not secrets.awskms:
                    logger.debug(
                        "secret_update_validate: target: %s has no inventory awskms key, skipping %s",
                        target_name,
                        token_path,
                    )
                    continue
                key = secrets.awskms.key
                secret_obj = ref_controller[token_path]
                if key != secret_obj.key:
                    if args.validate_targets:
                        logger.info("%s key mismatch", token_path)
                        ret_code = 1
                    else:
                        secret_obj.update_key(key)
                        ref_controller[token_path] = secret_obj

            elif type_name == KapitanReferencesTypes.AZKMS:
                if not secrets.azkey:
                    logger.debug(
                        "secret_update_validate: target: %s has no inventory azkms key, skipping %s",
                        target_name,
                        token_path,
                    )
                    continue
                secret_obj = ref_controller[token_path]
                key = secrets.azkms.key
                if key != secret_obj.key:
                    if args.validate_targets:
                        logger.info("%s key mismatch", token_path)
                        ret_code = 1
                    else:
                        secret_obj.update_key(key)
                        ref_controller[token_path] = secret_obj

            else:
                logger.info("Invalid secret %s, could not get type, skipping", token_path)

    sys.exit(ret_code)
