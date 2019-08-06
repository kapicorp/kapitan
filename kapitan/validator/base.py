import logging

logger = logging.getLogger(__name__)


class Validator(object):
    def __init__(self, cache_dir, **kwargs):
        self.cache_dir = cache_dir

    def validate(self, validate_obj, **kwargs):
        raise NotImplementedError
