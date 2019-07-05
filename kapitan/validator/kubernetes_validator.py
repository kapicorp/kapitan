import os
from functools import lru_cache

import yaml
import logging
import jsonschema

from kapitan.errors import RequestUnsuccessfulError, KubernetesManifestValidationError
from kapitan.validator.base import Validator
from kapitan.utils import make_request

DEFAULT_VERSION = '1.14.0'

logger = logging.getLogger(__name__)


class KubernetesManifestValidator(Validator):
    def __init__(self, cache_dir, **kwargs):
        super().__init__(cache_dir, **kwargs)
        self.schema_type = 'standalone-strict'
        self.file_path_format = 'v{}-%s/{}.json' % self.schema_type

    def validate(self, validate_obj, **kwargs):
        """
        validates validate_obj against json schema as specified by
        'kind' and 'version' in kwargs
        raises KubernetesManifestValidationError if validation fails, listing all the errors
        inside validate_obj
        """
        kind = kwargs.get('kind')
        version = kwargs.get('version', DEFAULT_VERSION)
        schema = self._get_schema(kind, version)
        v = jsonschema.Draft4Validator(schema)
        errors = sorted(v.iter_errors(validate_obj), key=lambda e: e.path)
        if errors:
            error_message = ''
            if 'file_path' in kwargs and 'target_name' in kwargs:
                error_message += 'invalid manifest for target "{}" at {}\n'.format(
                    kwargs.get('target_name'), kwargs.get('file_path'))

            error_message += '\n'.join(['{} {}'.format(list(error.path), error.message) for error in errors])
            raise KubernetesManifestValidationError(error_message)

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
        logger.debug("Fetching schema from {}".format(url))
        content, _ = make_request(url)
        if content is None:
            raise RequestUnsuccessfulError("schema failed to fetch from {}"
                                           "\nThe specified version or kind may not be supported".format(url))
        logger.debug("schema fetched  from {}".format(url))
        return yaml.safe_load(content)

    def _get_request_url(self, kind, version):
        return 'https://kubernetesjsonschema.dev/' + self.file_path_format.format(version, kind)

    def _get_cache_path(self, kind, version):
        return os.path.join(self.cache_dir, self.file_path_format.format(version, kind))
