"GCP secret manager secret retrieval module"
import os
import base64
import re
import json
import hashlib
from binascii import Error as b_error
from google.cloud import secretmanager
from kapitan.errors import KapitanError
from kapitan import cached
from kapitan.refs.base import RefError
from kapitan.refs.base64 import Base64Ref, Base64RefBackend
from kapitan.refs.base import REF_TOKEN_SUBVAR_PATTERN


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

        self.data = data
        self.project_id = project_id
        self.version_id = kwargs.get("version_id", "latest")
        super().__init__(self.data, **kwargs)
        self.type_name = "gsm"

    @classmethod
    def from_params(cls, data, ref_params):
        """
        GSM Secret type is read only and cannot generate a secret
        """
        raise GoogleSMError("GSM type does not support secondary functions")

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

    def compile(self):
        # XXX will only work if object read via backend

        if self.embed_refs:
            return self.compile_embedded()

        return f"?{{{self.type_name}:{self.path}:{self.version_id}:{self.hash[:8]}}}"

    def compile_embedded(self):
        dump = self.dump()
        # add version_id for serialization
        dump["version_id"] = self.version_id
        # if subvar is set, save path in 'embedded_subvar_path' key
        # TODO test subvar
        subvar = self.path.split("@")
        if len(subvar) > 1:
            dump["embedded_subvar_path"] = subvar[1]
        dump_data = base64.b64encode(json.dumps(dump).encode()).decode()
        return f"?{{{self.type_name}:{dump_data}:{self.version_id}:embedded}}"


class GoogleSMBackend(Base64RefBackend):
    def __init__(self, path, ref_type=GoogleSMSecret, **ref_kwargs):
        "init GoogleSMBackend ref backend type"
        super().__init__(path, ref_type, **ref_kwargs)
        self.type_name = "gsm"

    def __getitem__(self, ref_path):
        # remove the substring notation, if any
        ref_file_path = re.sub(REF_TOKEN_SUBVAR_PATTERN, "", ref_path)
        full_ref_path = os.path.join(self.path, ref_file_path)
        ref = self.ref_type.from_path(full_ref_path, **self.ref_kwargs)

        if ref is not None:
            ref.path = ref_path
            ref_path_data = "{}{}{}".format(ref_file_path, ref.data, ref.version_id)
            ref.hash = hashlib.sha256(ref_path_data.encode()).hexdigest()
            ref.token = "{}:{}:{}:{}".format(ref.type_name, ref.path, ref.version_id, ref.hash[:8])
            return ref

        raise KeyError(ref_path)
