from __future__ import print_function

import base64
import logging
import os
import sys

from kapitan.errors import KapitanError, RefHashMismatchError
from kapitan.refs.base import PlainRef, RefController, Revealer
from kapitan.refs.base64 import Base64Ref
from kapitan.refs.secrets.awskms import AWSKMSSecret
from kapitan.refs.secrets.gkms import GoogleKMSSecret
from kapitan.refs.secrets.gpg import GPGSecret, lookup_fingerprints
from kapitan.refs.secrets.vaultkv import VaultSecret
from kapitan.resources import inventory_reclass
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
    data = None

    if file_name is None:
        fatal_error("--file is required with --write")
    if file_name == "-":
        data = ""
        for line in sys.stdin:
            data += line
    else:
        with open(file_name) as fp:
            data = fp.read()

    if token_name.startswith("gpg:"):
        type_name, token_path = token_name.split(":")
        recipients = [dict((("name", name),)) for name in args.recipients]
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError(
                    "parameters.kapitan.secrets not defined in inventory of target {}".format(
                        args.target_name
                    )
                )

            recipients = kap_inv_params["secrets"]["gpg"]["recipients"]
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
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError(
                    "parameters.kapitan.secrets not defined in inventory of target {}".format(
                        args.target_name
                    )
                )

            key = kap_inv_params["secrets"]["gkms"]["key"]
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
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError(
                    "parameters.kapitan.secrets not defined in inventory of target {}".format(
                        args.target_name
                    )
                )

            key = kap_inv_params["secrets"]["awskms"]["key"]
        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.awskms.key and use --target-name"
            )
        secret_obj = AWSKMSSecret(data, key, encode_base64=args.base64)
        tag = "?{{awskms:{}}}".format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("base64:"):
        type_name, token_path = token_name.split(":")
        _data = data.encode()
        encoding = "original"
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = "base64"
        ref_obj = Base64Ref(_data, encoding=encoding)
        tag = "?{{base64:{}}}".format(token_path)
        ref_controller[tag] = ref_obj

    elif token_name.startswith("vaultkv:"):
        type_name, token_path = token_name.split(":")
        _data = data.encode()
        vault_params = {}
        encoding = "original"
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError(
                    "parameters.kapitan.secrets not defined in inventory of target {}".format(
                        args.target_name
                    )
                )

            vault_params = kap_inv_params["secrets"]["vaultkv"]
        if args.vault_auth:
            vault_params["auth"] = args.vault_auth
        if vault_params.get("auth") is None:
            raise KapitanError(
                "No Authentication type parameter specified. Specify it"
                " in parameters.kapitan.secrets.vaultkv.auth and use --target-name or use --vault-auth"
            )

        secret_obj = VaultSecret(_data, vault_params)
        tag = "?{{vaultkv:{}}}".format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("plain:"):
        type_name, token_path = token_name.split(":")
        _data = data.encode()
        encoding = "original"
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = "base64"
        ref_obj = PlainRef(_data, encoding=encoding)
        tag = "?{{plain:{}}}".format(token_path)
        ref_controller[tag] = ref_obj

    else:
        fatal_error(
            "Invalid token: {name}. Try using gpg/gkms/awskms/vaultkv/base64/plain:{name}".format(
                name=token_name
            )
        )


def secret_update(args, ref_controller):
    "Update secret gpg recipients/gkms/awskms key"
    # TODO --update *might* mean something else for other types
    token_name = args.update
    if token_name.startswith("gpg:"):
        # args.recipients is a list, convert to recipients dict
        recipients = [dict([("name", name),]) for name in args.recipients]
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            recipients = kap_inv_params["secrets"]["gpg"]["recipients"]
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
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            key = kap_inv_params["secrets"]["gkms"]["key"]
        if not key:
            raise KapitanError(
                "No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.gkms.key and use --target"
            )
        type_name, token_path = token_name.split(":")
        tag = "?{{gkms:{}}}".format(token_path)
        secret_obj = ref_controller[tag]
        secret_obj.update_key(key)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("awskms:"):
        key = args.key
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv["nodes"][args.target_name]["parameters"]["kapitan"]
            if "secrets" not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            key = kap_inv_params["secrets"]["awskms"]["key"]
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
    if file_name is None:
        fatal_error("--file is required with --reveal")
    try:
        if file_name == "-":
            out = revealer.reveal_raw_file(None)
            sys.stdout.write(out)
        elif file_name:
            for rev_obj in revealer.reveal_path(file_name):
                sys.stdout.write(rev_obj.content)
    except (RefHashMismatchError, KeyError):
        raise KapitanError("Reveal failed for file {name}".format(name=file_name))


def secret_update_validate(args, ref_controller):
    "Validate and/or update target secrets"
    # update gpg recipients/gkms/awskms key for all secrets in secrets_path
    # use --refs-path to set scanning path
    inv = inventory_reclass(args.inventory_path)
    targets = set(inv["nodes"].keys())
    secrets_path = os.path.abspath(args.refs_path)
    target_token_paths = search_target_token_paths(secrets_path, targets)
    ret_code = 0

    for target_name, token_paths in target_token_paths.items():
        kap_inv_params = inv["nodes"][target_name]["parameters"]["kapitan"]
        if "secrets" not in kap_inv_params:
            raise KapitanError("parameters.kapitan.secrets not defined in {}".format(target_name))

        try:
            recipients = kap_inv_params["secrets"]["gpg"]["recipients"]
        except KeyError:
            recipients = None
        try:
            gkey = kap_inv_params["secrets"]["gkms"]["key"]
        except KeyError:
            gkey = None
        try:
            awskey = kap_inv_params["secrets"]["awskms"]["key"]
        except KeyError:
            awskey = None
        try:
            vaultkv = kap_inv_params["secrets"]["vaultkv"]["auth"]
        except KeyError:
            vaultkv = None

        for token_path in token_paths:
            if token_path.startswith("?{gpg:"):
                if not recipients:
                    logger.debug(
                        "secret_update_validate: target: %s has no inventory gpg recipients, skipping %s",
                        target_name,
                        token_path,
                    )
                    continue
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
                        new_recipients = [dict([("fingerprint", f),]) for f in target_fingerprints]
                        secret_obj.update_recipients(new_recipients)
                        ref_controller[token_path] = secret_obj

            elif token_path.startswith("?{gkms:"):
                if not gkey:
                    logger.debug(
                        "secret_update_validate: target: %s has no inventory gkms key, skipping %s",
                        target_name,
                        token_path,
                    )
                    continue
                secret_obj = ref_controller[token_path]
                if gkey != secret_obj.key:
                    if args.validate_targets:
                        logger.info("%s key mismatch", token_path)
                        ret_code = 1
                    else:
                        secret_obj.update_key(gkey)
                        ref_controller[token_path] = secret_obj

            elif token_path.startswith("?{awskms:"):
                if not awskey:
                    logger.debug(
                        "secret_update_validate: target: %s has no inventory awskms key, skipping %s",
                        target_name,
                        token_path,
                    )
                    continue
                secret_obj = ref_controller[token_path]
                if awskey != secret_obj.key:
                    if args.validate_targets:
                        logger.info("%s key mismatch", token_path)
                        ret_code = 1
                    else:
                        secret_obj.update_key(awskey)
                        ref_controller[token_path] = secret_obj

            else:
                logger.info("Invalid secret %s, could not get type, skipping", token_path)

    sys.exit(ret_code)
