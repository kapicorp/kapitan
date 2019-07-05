import os
from functools import lru_cache

import requests
import yaml
import logging
import jsonschema

from kapitan.errors import RequestUnsuccessfulError, KubernetesManifestValidationError
from kapitan.validator.base import Validator
from kapitan.utils import make_request

DEFAULT_KUBERNETES_VERSION = '1.14.0'
# standalone is used for standalone json schema (i.e. without external $refs)
# strict is used as it behaves similarly to kubectl
# see https://github.com/garethr/kubernetes-json-schema#kubernetes-json-schemas for more info
SCHEMA_TYPE = 'standalone-strict'
FILE_PATH_FORMAT = 'v{}-%s/{}.json' % SCHEMA_TYPE

logger = logging.getLogger(__name__)


class KubernetesManifestValidator(Validator):
    def __init__(self, cache_dir, **kwargs):
        super().__init__(cache_dir, **kwargs)

    def validate(self, validate_instance, **kwargs):
        """
        validates validate_obj against json schema as specified by
        'kind' and 'version' in kwargs. if validate_obj is of type str, it will be
        used as the file path to the obj to be validated.
        raises KubernetesManifestValidationError if validation fails, listing all the errors
        inside validate_obj
        """
        output_path = kwargs.get('output_path', None)
        if isinstance(validate_instance, str):
            full_file_path = validate_instance
            with open(full_file_path, 'r') as fp:
                validate_instance = yaml.safe_load(fp.read())
        target_name = kwargs.get('target_name', '')
        kind = kwargs.get('kind')
        version = kwargs.get('version', DEFAULT_KUBERNETES_VERSION)
        schema = self._get_schema(kind, version)
        v = jsonschema.Draft4Validator(schema)
        errors = sorted(v.iter_errors(validate_instance), key=lambda e: e.path)
        if errors:
            error_message = 'invalid manifest for target "{}" at {}\n'.format(
                kwargs.get('target_name'), output_path)

            error_message += '\n'.join(['{} {}'.format(list(error.path), error.message) for error in errors])
            raise KubernetesManifestValidationError(error_message)
        else:
            logger.info("Validation: manifest validation successful for target '{}'"
                        " for {}".format(target_name, output_path))

    @lru_cache(maxsize=256)
    def _get_schema(self, kind, version):
        """gets json validation schema from web or cache"""
        schema = self._get_cached_schema(kind, version)
        if schema is None:
            schema = self._get_schema_from_web(kind, version)
            self._cache_schema(kind, version, schema)
        return schema

    def _cache_schema(self, kind, version, schema):
        cache_path = self._get_cache_path(kind, version)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w') as fp:
            yaml.safe_dump(schema, stream=fp, default_flow_style=False)

    def _get_cached_schema(self, kind, version):
        cache_path = self._get_cache_path(kind, version)
        if os.path.isfile(cache_path):
            with open(cache_path, 'r') as fp:
                return yaml.safe_load(fp.read())
        else:
            return None

    def _get_schema_from_web(self, kind, version):
        url = self._get_request_url(kind, version)
        logger.debug("Validation: fetching schema from {}".format(url))
        try:
            content, _ = make_request(url)
        except requests.exceptions.HTTPError:
            raise RequestUnsuccessfulError("Validation: schema failed to fetch from {}"
                                           "\nThe specified version '{}' or kind '{}' may not be supported".format(url, version, kind))
        logger.debug("Validation: schema fetched  from {}".format(url))
        return yaml.safe_load(content)

    def _get_request_url(self, kind, version):
        return 'https://kubernetesjsonschema.dev/' + FILE_PATH_FORMAT.format(version, kind)

    def _get_cache_path(self, kind, version):
        return os.path.join(self.cache_dir, FILE_PATH_FORMAT.format(version, kind))
