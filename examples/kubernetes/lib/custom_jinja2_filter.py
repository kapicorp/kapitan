import base64


def custom_jinja2_filter(string):
    """encodes a string using base64 schema"""
    return base64.b64encode(string.encode("UTF-8")).decode("UTF-8")
