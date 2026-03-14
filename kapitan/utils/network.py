"""Network utility helpers."""

import requests


def make_request(source):
    """Download the HTTP file at source and return its content and content type."""
    response = requests.get(source)
    if response.ok:
        return response.content, response.headers["Content-Type"]
    response.raise_for_status()
    return None, None
