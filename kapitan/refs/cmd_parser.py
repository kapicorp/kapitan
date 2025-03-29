"""
Reference handling command-line parser module for Kapitan.

This module provides functionality to:
- Write references to storage (secret encryption)
- Reveal references (secret decryption)
- Update reference keys/recipients
- Validate references against inventory configuration

References can be of various types:
- GPG: Uses GPG for encryption
- KMS: Various KMS implementations (Google, AWS, Azure)
- Vault: HashiCorp Vault integration (KV and Transit)
- Simple: Base64, plain text, environment variables

The module uses lazy loading to minimize dependencies - only importing
specific backend libraries when they are actually needed.
"""

from __future__ import print_function

import base64
import importlib
import logging
import mimetypes
import os
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union, cast

from kapitan.errors import KapitanError, RefError, RefHashMismatchError
from kapitan.inventory.model.references import (
    KapitanReferenceConfig,
    KapitanReferenceVaultKVConfig,
    KapitanReferenceVaultTransitConfig,
)
from kapitan.refs import KapitanReferencesTypes
from kapitan.refs.base import RefController, Revealer
from kapitan.resources import get_inventory
from kapitan.utils import fatal_error, search_target_token_paths

# Add typing for common return types
RefObject = Any  # Replace with actual type when available
SecretObject = Any  # Replace with actual type when available

logger = logging.getLogger(__name__)

# Module cache to avoid repeated imports
_class_cache = {}


def lazy_import(module_path: str, class_name: str) -> Type:
    """
    Dynamically import a class only when needed to reduce unnecessary dependencies.

    Args:
        module_path: The Python module path to import from
        class_name: The class name to import from the module

    Returns:
        The imported class

    Raises:
        KapitanError: If import fails due to missing dependencies
    """
    cache_key = f"{module_path}.{class_name}"

    if cache_key in _class_cache:
        return _class_cache[cache_key]

    try:
        module = importlib.import_module(module_path)
        imported_class = getattr(module, class_name)
        _class_cache[cache_key] = imported_class
        return imported_class
    except ImportError as e:
        raise KapitanError(
            f"Could not import {class_name} from {module_path}: {e}. Please install required dependencies."
        )


# ---------------------------------------------------------------------------
# Core helper functions for accessing and manipulating references
# ---------------------------------------------------------------------------


def get_backend_class(type_name: KapitanReferencesTypes) -> Type:
    """Get the appropriate backend class based on reference type"""
    backend_map = {
        KapitanReferencesTypes.GPG: ("kapitan.refs.secrets.gpg", "GPGSecret"),
        KapitanReferencesTypes.GKMS: ("kapitan.refs.secrets.gkms", "GoogleKMSSecret"),
        KapitanReferencesTypes.AWSKMS: ("kapitan.refs.secrets.awskms", "AWSKMSSecret"),
        KapitanReferencesTypes.AZKMS: ("kapitan.refs.secrets.azkms", "AzureKMSSecret"),
        KapitanReferencesTypes.BASE64: ("kapitan.refs.base64", "Base64Ref"),
        KapitanReferencesTypes.PLAIN: ("kapitan.refs.base", "PlainRef"),
        KapitanReferencesTypes.ENV: ("kapitan.refs.env", "EnvRef"),
        KapitanReferencesTypes.VAULTKV: ("kapitan.refs.secrets.vaultkv", "VaultSecret"),
        KapitanReferencesTypes.VAULTTRANSIT: ("kapitan.refs.secrets.vaulttransit", "VaultTransit"),
    }

    if type_name not in backend_map:
        raise KapitanError(f"Unknown backend type: {type_name}")

    module_name, class_name = backend_map[type_name]
    return lazy_import(module_name, class_name)


def lookup_fingerprints(recipients):
    """Import and use GPG functions only when needed"""
    module_path = "kapitan.refs.secrets.gpg"
    func_name = "lookup_fingerprints"
    return lazy_import(module_path, func_name)(recipients)


# Helper functions to reduce code duplication
def get_key_from_config(args, backend_config, type_name):
    """Helper function to get key from args or backend config"""
    key = args.key

    if backend_config:
        key = args.key or backend_config.key

    if not key:
        raise KapitanError(
            f"No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.{type_name}.key and use --target"
        )

    return key


def update_secret_key(tag, ref_controller, key):
    """Helper function to update key in secret object"""
    secret_obj = ref_controller[tag]
    secret_obj.update_key(key)
    ref_controller[tag] = secret_obj
    return secret_obj


def validate_or_update_kms_secret(args, ref_controller, token_path, target_key, secret_obj):
    """Helper function to validate or update KMS secrets"""
    if target_key != secret_obj.key:
        if args.validate_targets:
            logger.info("%s key mismatch", token_path)
            return 1
        else:
            secret_obj.update_key(target_key)
            ref_controller[token_path] = secret_obj
    return 0


# ---------------------------------------------------------------------------
# Helper functions for creating and managing different reference types
# ---------------------------------------------------------------------------


def create_simple_ref(
    type_name: KapitanReferencesTypes, data: Union[str, bytes], is_binary: bool, args: Any
) -> RefObject:
    """
    Helper to create simple references (Base64/Plain/Env).

    Handles data encoding and creates the appropriate reference object.

    Args:
        type_name: Type of reference to create (BASE64, PLAIN, ENV)
        data: The raw data to store in the reference
        is_binary: Whether the data is binary
        args: Command line arguments containing base64 flag

    Returns:
        The created reference object
    """
    RefClass = get_backend_class(type_name)
    _data = data if is_binary else data.encode()
    encoding = "original"

    if args.base64:
        _data = base64.b64encode(_data).decode()
        _data = _data.encode()
        encoding = "base64"

    return RefClass(_data, encoding=encoding)


def create_kms_secret(type_name, data, args, reference_backend_configs):
    """Helper to create KMS secrets (GKMS/AWSKMS/AZKMS)"""
    backend_name = type_name.value.lower()
    SecretClass = get_backend_class(type_name)

    backend_config = getattr(reference_backend_configs, backend_name, None)
    key = get_key_from_config(args, backend_config, backend_name)

    logger.debug(f"Using {backend_name} key {key}")
    return SecretClass(data, key, encode_base64=args.base64)


def create_vault_secret(type_name, data, is_binary, args, reference_backend_configs):
    """Helper to create Vault secrets (VAULTKV/VAULTTRANSIT)"""
    backend_name = type_name.value.lower()
    SecretClass = get_backend_class(type_name)

    _data = data if is_binary else data.encode()

    # Get the appropriate vault config class
    if type_name == KapitanReferencesTypes.VAULTKV:
        vault_params = KapitanReferenceVaultKVConfig()
        if reference_backend_configs.vaultkv:
            vault_params = reference_backend_configs.vaultkv
    else:  # VAULTTRANSIT
        vault_params = KapitanReferenceVaultTransitConfig()
        if reference_backend_configs.vaulttransit:
            vault_params = reference_backend_configs.vaulttransit

    # Set auth from args if provided
    if args.vault_auth:
        vault_params.auth = args.vault_auth

    # Validate auth is present
    if not vault_params.auth:
        raise KapitanError(
            "No Authentication type parameter specified. Specify it"
            " in parameters.kapitan.secrets.vaultkv.auth and use --target-name or use --vault-auth"
        )

    # Handle VAULTKV specific parameters
    if type_name == KapitanReferencesTypes.VAULTKV:
        kwargs = {}

        # Set mount
        mount = args.vault_mount
        if vault_params.mount:
            mount = vault_params.mount
        kwargs["mount_in_vault"] = mount

        # Set path in vault
        path_in_vault = args.vault_path
        if not path_in_vault:
            path_in_vault = args.write.split(":")[1]  # token path as default
        kwargs["path_in_vault"] = path_in_vault

        # Set key
        key = args.vault_key
        if key:
            kwargs["key_in_vault"] = key
        else:
            raise RefError("Could not create VaultSecret: vaultkv: key is missing")

        return SecretClass(_data, vault_params, **kwargs)
    else:  # VAULTTRANSIT
        return SecretClass(_data, vault_params)


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

        try:
            reference_backend_configs = inv.get_parameters(args.target_name).kapitan.secrets
        except (KeyError, AttributeError):
            raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

    type_name, token_path = token_name.split(":")

    try:
        type_name = KapitanReferencesTypes(type_name)
    except ValueError:
        raise KapitanError(
            f"Invalid token type: {type_name}. Try using gpg/gkms/awskms/azkms/vaultkv/vaulttransit/base64/plain/env"
        )

    tag = f"?{{{type_name}:{token_path}}}"

    # Process based on reference type using our helper functions
    secret_obj = None

    if type_name == KapitanReferencesTypes.GPG:
        # GPG is handled separately due to different parameters
        GPGSecret = get_backend_class(type_name)
        recipients = [dict((("name", name),)) for name in args.recipients]

        if reference_backend_configs.gpg:
            recipients = reference_backend_configs.gpg.recipients

        if not recipients:
            raise KapitanError(
                "No GPG recipients specified. Use --recipients or specify them in "
                + "parameters.kapitan.secrets.gpg.recipients and use --target"
            )

        secret_obj = GPGSecret(data, recipients, encode_base64=args.base64)

    elif type_name in [
        KapitanReferencesTypes.GKMS,
        KapitanReferencesTypes.AWSKMS,
        KapitanReferencesTypes.AZKMS,
    ]:
        # KMS backends (Google, AWS, Azure)
        secret_obj = create_kms_secret(type_name, data, args, reference_backend_configs)

    elif type_name in [KapitanReferencesTypes.VAULTKV, KapitanReferencesTypes.VAULTTRANSIT]:
        # Vault backends (KV, Transit)
        secret_obj = create_vault_secret(type_name, data, is_binary, args, reference_backend_configs)

    elif type_name in [
        KapitanReferencesTypes.BASE64,
        KapitanReferencesTypes.PLAIN,
        KapitanReferencesTypes.ENV,
    ]:
        # Simple reference types (Base64, Plain, Env)
        ref_obj = create_simple_ref(type_name, data, is_binary, args)
        ref_controller[tag] = ref_obj
        return

    # Store the secret object
    if secret_obj is not None:
        ref_controller[tag] = secret_obj


def secret_update(args: Any, ref_controller: RefController) -> None:
    """
    Update secret gpg recipients or KMS keys based on specified parameters.

    Args:
        args: Command line arguments
        ref_controller: Reference controller managing the secrets
    """
    # TODO --update *might* mean something else for other types
    token_name = args.update
    reference_backend_configs = KapitanReferenceConfig()

    # Load configuration from target if specified
    if args.target_name:
        inv = get_inventory(args.inventory_path)

        try:
            reference_backend_configs = inv.get_parameters(args.target_name).kapitan.secrets
        except (KeyError, AttributeError):
            # Target exists but doesn't have secrets configuration
            raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

    # Split token into type and path components
    type_name, token_path = token_name.split(":")

    # Validate the reference type is supported
    if type_name not in KapitanReferencesTypes:
        raise KapitanError(
            f"Invalid token type: {type_name}. Try using gpg/gkms/awskms/azkms/vaultkv/vaulttransit/base64/plain/env"
        )

    tag = f"?{{{type_name}:{token_path}}}"

    # Handle GPG references - requires updating recipients
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

    # Handle KMS references - requires updating keys
    elif type_name in [
        KapitanReferencesTypes.GKMS,
        KapitanReferencesTypes.AZKMS,
        KapitanReferencesTypes.AWSKMS,
    ]:
        # Get the appropriate backend config based on type
        backend_attr = type_name.value.lower()  # e.g., "gkms", "azkms", "awskms"
        backend_config = getattr(reference_backend_configs, backend_attr, None)

        # Get the key with proper error handling
        key = get_key_from_config(args, backend_config, backend_attr)

        # Update the secret object
        update_secret_key(tag, ref_controller, key)

    # Handle unsupported reference types
    else:
        fatal_error(f"Invalid token: {token_name}. Try using gpg/gkms/awskms/azkms:{token_name}")


def ref_reveal(args: Any, ref_controller: RefController) -> None:
    """
    Reveal secrets in specified file or reference and write to stdout.

    Args:
        args: Command line arguments containing file/ref-file/tag to reveal
        ref_controller: Reference controller managing the secrets

    Raises:
        KapitanError: If revealing the secret fails
    """
    revealer = Revealer(ref_controller)
    file_name = args.file
    reffile_name = args.ref_file
    tag_name = args.tag

    # Validate input parameters
    if file_name is None and reffile_name is None and tag_name is None:
        fatal_error("--file or --ref-file is required with --reveal")

    try:
        # Handle input from stdin
        if file_name == "-" or reffile_name == "-":
            out = revealer.reveal_raw_file(None)  # Read from stdin
            sys.stdout.write(out)
        # Handle file path
        elif file_name:
            for rev_obj in revealer.reveal_path(file_name):
                sys.stdout.write(rev_obj.content)
        # Handle reference file
        elif reffile_name:
            ref = ref_controller.ref_from_ref_file(reffile_name)
            sys.stdout.write(ref.reveal())
        # Handle direct tag
        elif tag_name:
            out = revealer.reveal_raw_string(tag_name)
            sys.stdout.write(out)
    except (RefHashMismatchError, KeyError) as e:
        # Add more context to the error message
        raise KapitanError(f"Reveal failed for file {file_name}: {str(e)}")


def secret_update_validate(args: Any, ref_controller: RefController) -> None:
    """
    Validate and/or update target secrets against inventory configurations.

    This function:
    1. Searches for secrets in the specified refs_path
    2. For each target's secrets, checks if they match inventory configuration
    3. Either reports mismatches (with --validate-targets) or updates them

    Args:
        args: Command line arguments
        ref_controller: Reference controller managing the secrets

    Returns:
        None, but exits with non-zero code if validation fails
    """
    # update gpg recipients/gkms/awskms key for all secrets in secrets_path
    # use --refs-path to set scanning path
    inv = get_inventory(args.inventory_path)
    targets = set(inv.targets.keys())  # All available targets
    secrets_path = os.path.abspath(args.refs_path)
    target_token_paths = search_target_token_paths(secrets_path, targets)
    ret_code = 0  # Track validation failures

    # Iterate through each target and its tokens
    for target_name, token_paths in target_token_paths.items():
        # Get the target's secrets configuration
        secrets = inv.get_parameters(target_name).kapitan.secrets
        if not secrets:
            raise KapitanError(f"parameters.kapitan.secrets not defined in {target_name}")

        # Process each secret token found for this target
        for token_path in token_paths:
            # Extract the secret type from the token path
            type_name = re.match(r"\?\{(\w+):", token_path).group(1)

            # Handle different secret types
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
                # Fix bug: incorrect key comparison
                if key != secret_obj.key:  # was: if secrets.gpg.key != key
                    ret_code = max(
                        ret_code,
                        validate_or_update_kms_secret(args, ref_controller, token_path, key, secret_obj),
                    )

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
                ret_code = max(
                    ret_code, validate_or_update_kms_secret(args, ref_controller, token_path, key, secret_obj)
                )

            elif type_name == KapitanReferencesTypes.AZKMS:
                # Fix bug: wrong attribute name
                if not secrets.azkms:  # was: secrets.azkey
                    logger.debug(
                        "secret_update_validate: target: %s has no inventory azkms key, skipping %s",
                        target_name,
                        token_path,
                    )
                    continue
                secret_obj = ref_controller[token_path]
                key = secrets.azkms.key
                ret_code = max(
                    ret_code, validate_or_update_kms_secret(args, ref_controller, token_path, key, secret_obj)
                )

            else:
                logger.info("Invalid secret %s, could not get type, skipping", token_path)

    sys.exit(ret_code)
