"GCP secret manager secret retrieval module"
import logging
import os
import base64
from binascii import Error as b_error
from google.cloud import secretmanager
from kapitan.errors import KapitanError
from kapitan import cached
from kapitan.refs.base import RefError
from kapitan.refs.base64 import Base64Ref, Base64RefBackend

logger = logging.getLogger(__name__)


class GoogleSMError(KapitanError):
    " Generic Google Secret Manager error "
    pass


def gsm_obj():
    if not cached.gsm_obj:
        gsm_client = secretmanager.SecretManagerServiceClient()
        cached.gsm_obj = gsm_client
    return cached.gsm_obj


class GoogleSMSecret(Base64Ref):
    """
    Google Secret Manager (read only) support
    """

    def __init__(self, data, project_id, **kwargs):
        # TODO add version from user input
        self.data = data
        self.project_id = project_id
        self.version_id = "latest"
        super().__init__(self.data, **kwargs)
        self.type_name = "gsm"

    @classmethod
    def from_param(cls, data, ref_params):
        """
        Return new GoogleSMSecret from data and ref_params: target_name
        project_id will be grabbed from the inventory via target_name
        """
        try:
            target_name = ref_params.kwargs["target_name"]
            if target_name is None:
                raise ValueError("target_name not set")
            target_inv = cached.inv["nodes"].get(target_name, None)
            if target_inv is None:
                raise ValueError("target_inv not set")

            project_id = target_inv["parameters"]["kapitan"]["secrets"]["gsm"]["project_id"]
            return cls(data, project_id, **ref_params.kwargs)
        except KeyError:
            raise RefError("Could not decode GoogleSMSecret: target_name missing")

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return super().from_path(ref_full_path, **kwargs)

    def reveal(self):
        "Returns the secret pertaining to a secret_id"
        # can't use super().reveal() as we want bytes
        try:
            _secret_id = base64.b64decode(self.data)
        except b_error:
            exit("non-alphabet characters in the data")

        secret_id = _secret_id.decode("UTF-8").rstrip()
        return self._access_secret_version(secret_id)

    def _access_secret_version(self, secret_id):
        """
        Retrieves the secret from Google Secret Manager
        :Returns: secret in plain text
        """
        try:
            name = gsm_obj().secret_version_path(self.project_id, secret_id, self.version_id)
            response = gsm_obj().access_secret_version(name)
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            raise GoogleSMError(e)

    def dump(self):
        """
        Returns a dict with key/value to be serialized
        """
        return {
            "data": self.data,
            "encoding": self.encoding,
            "project_id": self.project_id,
            "type": self.type_name,
        }


class GoogleSMBackend(Base64RefBackend):
    def __init__(self, path, ref_type=GoogleSMSecret, **ref_kwargs):
        "init GoogleSMBackend ref backend type"
        super().__init__(path, ref_type, **ref_kwargs)
        self.type_name = "gsm"
