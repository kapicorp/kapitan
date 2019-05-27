class Dependency(object):
    cache_dir = 'compiled/.kapitan_cache'

    def __init__(self, source_uri, output_path):
        self.source_uri = source_uri
        self.output_path = output_path

    def fetch(self):
        pass


